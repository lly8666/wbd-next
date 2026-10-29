//! PLAN026: one timer-free per-lane authenticated liveness policy.
//! Only the actual post-AEAD+unique-PN receive site may call
//! on_authenticated_control/on_authenticated_business. Raw TCP ACK or
//! user-space timer ticks cannot manufacture peer activity.
//! The native I/O worker owns this value, no Arc, goroutine or timer thread.
#![forbid(unsafe_code)]

const SECOND_NS:u64=1_000_000_000;
const MIN_RETRY_NS:u64=SECOND_NS;

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) struct HealthPolicy {
    interval_ns:u64,
    dead_ns:u64,
    dormant_ns:Option<u64>,
}
impl HealthPolicy {
    pub(crate) const DEFAULT_INTERVAL_NS:u64=15*SECOND_NS;
    pub(crate) const DEFAULT_DEAD_NS:u64=90*SECOND_NS;

    pub(crate) fn new(interval_ns:u64,dead_ns:u64,dormant_ns:Option<u64>)->Option<Self>{
        if !(SECOND_NS..=3600*SECOND_NS).contains(&interval_ns)
            || dead_ns<interval_ns.checked_mul(3)?
            || dead_ns>86400*SECOND_NS
            || dormant_ns==Some(0) {
            return None
        }
        Some(Self{interval_ns,dead_ns,dormant_ns})
    }
    pub(crate) fn default_connected()->Self{
        Self::new(Self::DEFAULT_INTERVAL_NS,Self::DEFAULT_DEAD_NS,None)
            .expect("valid fixed health defaults")
    }
    pub(crate) fn interval_ns(self)->u64{self.interval_ns}
    pub(crate) fn dead_ns(self)->u64{self.dead_ns}
    pub(crate) fn dormant_ns(self)->Option<u64>{self.dormant_ns}
}

/// A health send is a single AEAD kind1 control, never application progress.
/// Native owner decides if an already-ready authenticated M2/Quality control
/// can carry the same health hint; it must not emit a second control packet.
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(crate) enum ControlDue { None, Health, DeadPeer }

#[derive(Clone,Copy,Debug)]
pub(crate) struct HealthClock {
    policy:HealthPolicy,
    attached_at:u64,
    last_authenticated:Option<u64>,
    last_business:u64,
    next_health:u64,
    retry_not_before:u64,
    peer_idle:Option<(u64,u64)>,
    peer_write_closed:bool,
    disconnected:bool,
}
impl HealthClock {
    pub(crate) fn new(policy:HealthPolicy,at:u64)->Self{
        Self{policy,attached_at:at,last_authenticated:None,
            last_business:at,next_health:at.saturating_add(policy.interval_ns),
            retry_not_before:at,peer_idle:None,peer_write_closed:false,
            disconnected:false}
    }
    pub(crate) fn on_authenticated_control(&mut self,at:u64){
        if at>=self.attached_at {
            self.last_authenticated=Some(self.last_authenticated.map_or(at,|old|old.max(at)));
        }
    }
    pub(crate) fn on_authenticated_business(&mut self,at:u64){
        self.on_authenticated_control(at);
        self.on_local_business(at);
    }
    pub(crate) fn on_local_business(&mut self,at:u64){
        if at>=self.last_business {self.last_business=at}
    }
    /// Set only from an authenticated and unique remote Health/Quality TLV.
    /// The peer's idle claim never advances local payload activity.
    pub(crate) fn on_peer_idle_hint(&mut self,at:u64,idle_ns:u64){
        self.on_authenticated_control(at);
        if at>=self.attached_at &&
            self.peer_idle.is_none_or(|(last,_)|at>=last) {
            self.peer_idle=Some((at,idle_ns));
        }
    }
    /// A peer FIN must have been verified in sequence by cold/transport.
    pub(crate) fn on_verified_peer_fin(&mut self){self.peer_write_closed=true}
    pub(crate) fn clear_on_new_incarnation(&mut self,now:u64){
        *self=Self::new(self.policy,now);
    }
    /// Accepted is a synchronous definite driver copy, not remote receipt.
    /// Failed/uncertain copies do not postpone a required heartbeat for 15s.
    pub(crate) fn on_health_send_result(&mut self,at:u64,accepted:bool){
        if accepted {
            self.next_health=at.saturating_add(self.policy.interval_ns);
            self.retry_not_before=at;
        }else{
            self.retry_not_before=at.saturating_add(MIN_RETRY_NS);
        }
    }
    /// A successfully sent Quality/Receipt carrying the *same* idle hint
    /// satisfies Health; an ordinary Receipt without hint does not.
    pub(crate) fn on_merged_control_sent(&mut self,at:u64,contains_health:bool){
        if contains_health {self.on_health_send_result(at,true)}
    }
    pub(crate) fn unhealthy(&self,now:u64)->bool{
        let from=self.last_authenticated.unwrap_or(self.attached_at);
        !self.disconnected && now>=from &&
            now.saturating_sub(from)>=self.policy.dead_ns
    }
    pub(crate) fn control_due(&self,now:u64)->ControlDue{
        if self.disconnected{return ControlDue::None}
        if self.unhealthy(now){return ControlDue::DeadPeer}
        if now>=self.next_health && now>=self.retry_not_before {
            ControlDue::Health
        }else{ControlDue::None}
    }
    pub(crate) fn next_deadline(&self)->Option<u64>{
        if self.disconnected{return None}
        let from=self.last_authenticated.unwrap_or(self.attached_at);
        Some(from.saturating_add(self.policy.dead_ns)
            .min(self.next_health.max(self.retry_not_before)))
    }
    /// Server-side DORMANT requires client's FIN commitment AND
    /// actual local payload idle; missing keepalives alone cannot do it.
    pub(crate) fn server_can_dormant(&self,now:u64)->bool{
        self.policy.dormant_ns.is_some_and(|idle|
            self.peer_write_closed && now>=self.last_business &&
            now-self.last_business>=idle)
    }
    /// Client may request orderly dormancy only with recent authenticated
    /// remote idle evidence. The server must still wait for the real FIN.
    pub(crate) fn client_can_offer_fin(&self,now:u64)->bool{
        let Some(idle)=self.policy.dormant_ns else{return false};
        if now<self.last_business || now-self.last_business<idle{return false}
        let Some((at,peer_idle))=self.peer_idle else{return false};
        now>=at && now-at<=self.policy.interval_ns.saturating_mul(2)
            && peer_idle>=idle
    }
    pub(crate) fn stopped(&mut self){self.disconnected=true}
}

#[cfg(test)]
mod tests {
    use super::*;
    const S:u64=SECOND_NS;
    fn default()->HealthClock{HealthClock::new(HealthPolicy::default_connected(),0)}
    #[test]
    fn original_15s_90s_and_three_intervals_are_enforced(){
        assert!(HealthPolicy::new(15*S,90*S,None).is_some());
        assert!(HealthPolicy::new(30*S,89*S,None).is_none());
        assert!(HealthPolicy::new(0,90*S,None).is_none());
        assert!(HealthPolicy::new(15*S,90*S,Some(0)).is_none());
        assert_eq!(default().next_deadline(),Some(15*S));
    }
    #[test]
    fn authenticated_health_keeps_idle_tunnel_alive_without_business(){
        let mut c=default();
        for tick in 1..=12 {
            let now=tick*15*S;
            assert_eq!(c.control_due(now),ControlDue::Health);
            c.on_health_send_result(now,true);
            c.on_authenticated_control(now);
            assert!(!c.unhealthy(now));
        }
        assert_eq!(c.last_business,0);
        assert!(!c.server_can_dormant(180*S));
    }
    #[test]
    fn failure_retries_at_one_second_without_claiming_keepalive_success(){
        let mut c=default();
        assert_eq!(c.control_due(15*S),ControlDue::Health);
        c.on_health_send_result(15*S,false);
        assert_eq!(c.control_due(15*S+1),ControlDue::None);
        assert_eq!(c.next_deadline(),Some(16*S));
        assert_eq!(c.control_due(16*S),ControlDue::Health);
        c.on_merged_control_sent(16*S,false);
        assert_eq!(c.control_due(16*S),ControlDue::Health);
        c.on_merged_control_sent(16*S,true);
        assert_eq!(c.next_deadline(),Some(31*S));
    }
    #[test]
    fn missing_authenticated_records_becomes_dead_not_dormant(){
        let mut c=HealthClock::new(HealthPolicy::new(15*S,90*S,Some(60*S)).unwrap(),0);
        assert_eq!(c.control_due(89*S),ControlDue::Health);
        assert_eq!(c.control_due(90*S),ControlDue::DeadPeer);
        assert!(!c.server_can_dormant(180*S));
        c.on_authenticated_control(90*S);
        assert!(!c.unhealthy(120*S));
        assert!(!c.server_can_dormant(120*S));
    }
    #[test]
    fn idle_hint_is_not_business_and_server_requires_verified_fin(){
        let policy=HealthPolicy::new(15*S,90*S,Some(60*S)).unwrap();
        let mut client=HealthClock::new(policy,0);
        let mut server=HealthClock::new(policy,0);
        client.on_peer_idle_hint(60*S,60*S);
        assert!(client.client_can_offer_fin(60*S));
        assert!(!server.server_can_dormant(70*S));
        server.on_authenticated_control(70*S);
        assert!(!server.server_can_dormant(70*S));
        server.on_verified_peer_fin();
        assert!(server.server_can_dormant(70*S));
        client.on_local_business(71*S);
        assert!(!client.client_can_offer_fin(72*S));
        assert!(!client.client_can_offer_fin(100*S));
    }
    #[test]
    fn stale_health_and_replaced_incarnation_are_not_alive_or_fin(){
        let policy=HealthPolicy::new(15*S,90*S,Some(60*S)).unwrap();
        let mut c=HealthClock::new(policy,0);
        c.on_peer_idle_hint(60*S,60*S);
        assert!(!c.client_can_offer_fin(91*S));
        c.on_verified_peer_fin();
        c.clear_on_new_incarnation(100*S);
        assert!(!c.server_can_dormant(200*S));
        assert!(!c.client_can_offer_fin(200*S));
        c.stopped();
        assert_eq!(c.next_deadline(),None);
        assert_eq!(c.control_due(300*S),ControlDue::None);
    }
}

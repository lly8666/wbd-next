//! Bounded, generation-scoped Linux IPv4 link/PMTU cache.
//!
//! Only the singleton M0 NETLINK_ROUTE revision source is subscribed; this
//! module installs no second route watcher, does not authorize raw/Go V4, and
//! never accesses sysfs, UDP route probe, or network device per DATA packet.
//! A missed/unhealthy watcher, interface replacement, or explicit send error
//! refuses further send until trusted owner rotates. The original kernel
//! IP_HDRINCL/DF enforcement remains authoritative on an actual send.
use crate::linux_packet_preflight::{
    observe_interface_mtu, observe_ipv4_route_mtu, PreflightError,
};
use crate::linux_route_events::{self,RouteEvents};
use std::net::Ipv4Addr;
use std::sync::{Arc,Mutex};
use std::time::{Duration,Instant};

const MAX_CACHE_AGE:Duration=Duration::from_secs(1);
const COALESCE:Duration=Duration::from_millis(100);
#[derive(Debug,Clone,Copy,Eq,PartialEq)]
pub enum BudgetError {
    Unavailable,
    ChangedOrInvalid,
    Deferred,
}
#[derive(Clone,Copy)]
struct Snapshot{
    revision:u64,
    checked_at:Instant,
    dest:Option<Ipv4Addr>,
    route_mtu:u32,
    permanently_invalid:bool,
}
/// Per-owner cache, not global mutable route state. All kernel reads are on
/// owner install, revision change, destination change or bounded TTL expiry.
pub struct ScopedRouteBudget{
    watcher:Arc<RouteEvents>,
    ifname:String,
    ifindex:u32,
    initial_link_mtu:u32,
    generation:u32,
    state:Mutex<Snapshot>,
}
impl ScopedRouteBudget{
    pub fn open(ifname:&str,ifindex:u32,generation:u32,
                initial_link_mtu:u32)->Result<Self,BudgetError>{
        if generation==0||ifindex==0||initial_link_mtu<68 {
            return Err(BudgetError::Unavailable)
        }
        // Subscription before the initial sample prevents an unaccounted
        // change between the first MTU read and a new watcher registration.
        let watcher=linux_route_events::subscribe();
        let before=watcher.snapshot();
        if !before.healthy{return Err(BudgetError::Unavailable)}
        let got=observe_interface_mtu(ifname,ifindex)
            .map_err(|_|BudgetError::Unavailable)?;
        if got.kernel_mtu!=initial_link_mtu {
            return Err(BudgetError::ChangedOrInvalid)
        }
        let after=watcher.snapshot();
        if !after.healthy||after.revision!=before.revision{
            return Err(BudgetError::ChangedOrInvalid)
        }
        Ok(Self{watcher,ifname:ifname.to_owned(),ifindex,
            initial_link_mtu,generation,
            state:Mutex::new(Snapshot{revision:after.revision,
                checked_at:Instant::now(),dest:None,
                route_mtu:initial_link_mtu,permanently_invalid:false})})
    }
    pub fn generation(&self)->u32{self.generation}
    /// Called ONLY after an observed kernel device/MTU/route loss or an
    /// uncertain raw short send. The caller's already sealed records survive
    /// and are NOT blindly rewrapped or retried on an ambiguous path.
    pub fn invalidate(&self){
        let mut v=self.state.lock().unwrap_or_else(|e|e.into_inner());
        v.permanently_invalid=true;
    }
    pub fn is_invalid(&self)->bool{
        self.state.lock().unwrap_or_else(|e|e.into_inner()).permanently_invalid
    }
    fn needs_refresh(state:Snapshot,current_rev:u64,now:Instant,
                     dest:Option<Ipv4Addr>)->Result<bool,BudgetError>{
        if state.permanently_invalid{return Err(BudgetError::ChangedOrInvalid)}
        if current_rev!=state.revision &&
            now.duration_since(state.checked_at)<COALESCE{
            return Err(BudgetError::Deferred)
        }
        Ok(current_rev!=state.revision||
            now.duration_since(state.checked_at)>=MAX_CACHE_AGE||
            state.dest!=dest)
    }
    fn check(&self,dest:Option<Ipv4Addr>)->Result<usize,BudgetError>{
        let now=Instant::now();
        let before=self.watcher.snapshot();
        if !before.healthy{return Err(BudgetError::Unavailable)}
        let mut state=self.state.lock().unwrap_or_else(|e|e.into_inner());
        if !Self::needs_refresh(*state,before.revision,now,dest)?{
            // Recheck *after* acquiring the owner mutex: do not return a
            // cached budget if the watcher changed while waiting for lock.
            let after=self.watcher.snapshot();
            if !after.healthy || after.revision!=before.revision {
                return Err(BudgetError::ChangedOrInvalid)
            }
            return Ok(state.route_mtu as usize)
        }
        let new_budget=if let Some(ip)=dest{
            let observation=observe_ipv4_route_mtu(&self.ifname,self.ifindex,ip)
                .map_err(|_:PreflightError|BudgetError::Unavailable)?;
            if observation.interface_mtu!=self.initial_link_mtu {
                state.permanently_invalid=true;
                return Err(BudgetError::ChangedOrInvalid)
            }
            observation.route_mtu
        }else{
            let observation=observe_interface_mtu(&self.ifname,self.ifindex)
                .map_err(|_:PreflightError|BudgetError::Unavailable)?;
            if observation.kernel_mtu!=self.initial_link_mtu {
                state.permanently_invalid=true;
                return Err(BudgetError::ChangedOrInvalid)
            }
            observation.kernel_mtu
        };
        let after=self.watcher.snapshot();
        if !after.healthy||after.revision!=before.revision{
            // A change concurrent with refreshing must never stamp a stale
            // budget as current. Next send reobserves after debounce.
            return Err(BudgetError::ChangedOrInvalid)
        }
        state.route_mtu=new_budget.min(self.initial_link_mtu);
        state.revision=after.revision;
        state.checked_at=Instant::now();
        state.dest=dest;
        Ok(state.route_mtu as usize)
    }
    /// TX route lookup is to the configured IPv4 packet destination.
    pub fn send_budget(&self,destination:Ipv4Addr)->Result<usize,BudgetError>{
        self.check(Some(destination))
    }
    /// RX bound is local link MTU, never a new route to the remote address.
    pub fn receive_budget(&self)->Result<usize,BudgetError>{
        self.check(None)
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn r1_m4_pack_cache_revision_storm_ttl_route_switch_and_poison(){
        let now=Instant::now();
        let initial=Snapshot{revision:9,checked_at:now,
            dest:Some(Ipv4Addr::LOCALHOST),route_mtu:1500,
            permanently_invalid:false};
        assert_eq!(ScopedRouteBudget::needs_refresh(initial,9,now,
            Some(Ipv4Addr::LOCALHOST)),Ok(false));
        assert_eq!(ScopedRouteBudget::needs_refresh(initial,10,now,
            Some(Ipv4Addr::LOCALHOST)),Err(BudgetError::Deferred));
        assert_eq!(ScopedRouteBudget::needs_refresh(initial,10,
            now+COALESCE,Some(Ipv4Addr::LOCALHOST)),Ok(true));
        assert_eq!(ScopedRouteBudget::needs_refresh(initial,9,
            now+MAX_CACHE_AGE,Some(Ipv4Addr::LOCALHOST)),Ok(true));
        assert_eq!(ScopedRouteBudget::needs_refresh(initial,9,now,
            Some(Ipv4Addr::new(127,0,0,2))),Ok(true));
        assert_eq!(ScopedRouteBudget::needs_refresh(Snapshot{
            permanently_invalid:true,..initial},9,now,None),
            Err(BudgetError::ChangedOrInvalid));
    }

    #[test]
    fn r1_m4_012_route_storm_ifindex_mtu_down_up_and_fail_closed(){
        let now=Instant::now();
        let baseline=Snapshot{revision:41,checked_at:now,
            dest:Some(Ipv4Addr::new(127,0,0,1)),route_mtu:1500,
            permanently_invalid:false};
        // Before debounce no cached MTU is emitted during a storm.
        for revision in 42..202{
            assert_eq!(ScopedRouteBudget::needs_refresh(baseline,revision,
                now+Duration::from_millis(50),baseline.dest),
                Err(BudgetError::Deferred));
            assert_eq!(ScopedRouteBudget::needs_refresh(baseline,revision,
                now+Duration::from_millis(100),baseline.dest),Ok(true));
        }
        // Revised route, independent destination, and conservative TTL
        // must re-check observed ifindex/link/route kernel facts.
        for destination in [Ipv4Addr::new(127,0,0,2),
                            Ipv4Addr::new(127,0,0,3)] {
            assert_eq!(ScopedRouteBudget::needs_refresh(baseline,41,now,
                Some(destination)),Ok(true));
        }
        let invalid=Snapshot{permanently_invalid:true,..baseline};
        for r in [41,42,1000]{
            assert_eq!(ScopedRouteBudget::needs_refresh(invalid,r,
                now+Duration::from_secs(10),baseline.dest),
                Err(BudgetError::ChangedOrInvalid));
        }
        let lo=crate::linux_packet_preflight::interface_index("lo").unwrap();
        let original=observe_interface_mtu("lo",lo).unwrap();
        assert!(original.kernel_mtu>=68);
        // An injected wrong expected ifindex genuinely probes the Linux
        // kernel and fails before privileged raw/TUN opens.
        assert!(observe_interface_mtu("lo",lo.saturating_add(1)).is_err());
        assert!(ScopedRouteBudget::open("lo",lo,0,original.kernel_mtu).is_err());
        assert!(ScopedRouteBudget::open("lo",lo,17,original.kernel_mtu+1).is_err());
    }
    #[test]
    fn r1_m4_pack_actual_linux_interface_preflight_no_socket_or_raw(){
        // No privileged raw fd or network packet is created here.
        let index=crate::linux_packet_preflight::interface_index("lo").unwrap();
        let real=observe_interface_mtu("lo",index).unwrap();
        assert_eq!(real.ifindex,index);
        assert!(real.kernel_mtu>=68);
        assert!(observe_interface_mtu("lo",index+1).is_err());
    }
}

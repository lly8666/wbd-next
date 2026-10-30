//! PLAN027 Windows single Rust native Auto actor. One low-rate turn inside
//! the existing native worker, fed by authenticated sampled Quality and
//! independently normalized actual closed-block k. No hotpath controller.
#![allow(dead_code)]
use std::collections::VecDeque;
const S:u64=1_000_000_000;
#[derive(Clone,Copy)]
struct Point{at:u64,counters:[u64;30]}
#[derive(Clone,Copy)]
struct Window{sent:u64,observed:u64,missing:u64,unknown:u64}
fn window(now:&[u64;30],then:&[u64;30],offset:usize)->Option<Window>{
    let mut d=[0u64;5];
    for i in 0..5{d[i]=now[offset+i].checked_sub(then[offset+i])?}
    let observed=d[1].checked_add(d[2])?;
    if d[0]!=observed.checked_add(d[3])?.checked_add(d[4])?{return None}
    Some(Window{sent:d[0],observed,missing:d[2],unknown:d[3].saturating_add(d[4])})
}
fn idx_at_or_before(points:&VecDeque<Point>,now:u64,age:u64)->Option<usize>{
    points.iter().rposition(|x|x.at<=now.saturating_sub(age))
}
fn parity(profile:u8,k:usize)->usize{
    const N:[usize;7]=[1,1,3,1,3,1,5];
    const D:[usize;7]=[8,4,8,2,4,1,4];
    let n=N[profile as usize];let d=D[profile as usize];
    (k*n+d-1)/d
}
fn residual(k:usize,r:usize,p:f64)->f64{
    if p<=0.0{return 0.0}
    if p>=1.0{return 1.0}
    let n=k+r-1;
    let mut xprob=(1.0-p).powi(n as i32);
    let mut tail=0.0;
    for x in 0..=n{
        if x>=r{tail+=xprob}
        if x<n{xprob*=((n-x) as f64)/((x+1) as f64)*p/(1.0-p)}
    }
    (p*tail).min(1.0)
}
fn guarded(khist:&[u64;16],profile:u8,p:f64,_sampled_sources:u64)->f64{
    // Actual k is a full closed-block distribution; first-send loss is
    // an independent bounded PN sample. Normalize k within its own cohort.
    let mut total=0.0;let mut weighted=0.0;
    for (idx,&blocks) in khist.iter().enumerate(){
        let k=idx+1;let w=(blocks as f64)*(k as f64);
        total+=w;weighted+=w*residual(k,parity(profile,k),p);
    }
    if total==0.0{return 1.0}
    (weighted/total).min(1.0)
}
/// Returned revision is a *request*. Only an actual quiescent Rust
/// FixedStream revision change, followed by first-copy/M2 proof, is Applied.
#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub(super) struct GradeIntent{pub(super) profile:u8,pub(super) revision:u64}
pub(super) struct NativeAutoActor{
    profile:u8,revision:u64,aggressive:bool,
    history:VecDeque<Point>,next_due:u64,rising:u8,
    down_since:Option<u64>,down_last_valid:Option<u64>,
    down_sources:u64,down_windows:u8,last_down:Option<u64>,
    // A candidate does not mutate profile/revision until native commit.
    proposed:Option<GradeIntent>,
}
impl NativeAutoActor{
    pub(super) fn new(profile:u8,revision:u64,aggressive:bool,now:u64)->Self{
        Self{profile,revision,aggressive,history:VecDeque::with_capacity(12),
            next_due:now.saturating_add(2*S),rising:0,
            down_since:None,down_last_valid:None,
            down_sources:0,down_windows:0,last_down:None,
            proposed:None}
    }
    pub(super) fn deadline(&self)->u64{self.next_due}
    pub(super) fn profile(&self)->u8{self.profile}
    pub(super) fn revision(&self)->u64{self.revision}
    fn clear_down(&mut self){
        self.down_since=None;self.down_last_valid=None;
        self.down_sources=0;self.down_windows=0;
    }
    pub(super) fn resync(&mut self,profile:u8,revision:u64,now:u64){
        self.profile=profile;self.revision=revision;
        self.history.clear();self.rising=0;self.clear_down();
        self.next_due=now.saturating_add(2*S);
        self.proposed=None;
    }
    fn propose(&mut self,profile:u8)->Option<GradeIntent>{
        let revision=self.revision.checked_add(1)?;
        let intent=GradeIntent{profile,revision};
        self.proposed=Some(intent);
        Some(intent)
    }
    pub(super) fn commit(&mut self,intent:GradeIntent,now:u64){
        if self.proposed==Some(intent){
            let down=intent.profile<self.profile;
            self.resync(intent.profile,intent.revision,now);
            if down{self.last_down=Some(now)}
        }
    }
    /// On missing/censored/host-limited M2 no grade changes. An unknown
    /// actual-k cohort may pause <=6s of prior genuine low-loss proof,
    /// but cannot add phantom evidence or itself request a downshift.
    fn invalid(&mut self,now:u64)->Option<GradeIntent>{
        self.rising=0;
        if self.down_last_valid.is_none_or(|v|now.saturating_sub(v)>6*S){
            self.clear_down();
        }
        None
    }
    pub(super) fn evaluate(&mut self,now:u64,counters:[u64;30])->Option<GradeIntent>{
        if now<self.next_due{return None}
        self.next_due=now.saturating_add(2*S);
        self.history.push_back(Point{at:now,counters});
        if self.history.len()>12{self.history.pop_front();}
        let Some(fidx)=idx_at_or_before(&self.history,now,2*S)else{return None};
        let Some(sidx)=idx_at_or_before(&self.history,now,8*S)else{return None};
        let steps=self.history.len()-1-sidx;
        let Some(hidx)=sidx.checked_sub(steps)else{return None};
        let (fast,slow,hist)=(self.history[fidx],self.history[sidx],self.history[hidx]);

        let Some(f)=window(&counters,&fast.counters,0)else{return self.invalid(now)};
        let Some(s)=window(&counters,&slow.counters,5)else{return self.invalid(now)};
        if f.observed<64||s.observed<64||f.sent==0||s.sent==0||
            (f.observed as f64)/(f.sent as f64)<0.9||
            (s.observed as f64)/(s.sent as f64)<0.9||
            (f.unknown as f64)/(f.sent as f64)>0.2||
            (s.unknown as f64)/(s.sent as f64)>0.2{return self.invalid(now)}
        let Some(capacity)=counters[11].checked_sub(hist.counters[11])
            else{return self.invalid(now)};
        if capacity>0{return self.invalid(now)}
        let Some(reports)=counters[10].checked_sub(slow.counters[10])
            else{return self.invalid(now)};
        if reports==0{return self.invalid(now)}
        let Some(lag)=counters[12].checked_sub(slow.counters[12])
            else{return self.invalid(now)};
        let Some(samples)=counters[13].checked_sub(slow.counters[13])
            else{return self.invalid(now)};
        if samples==0||lag/samples>6*S{return self.invalid(now)}
        let mut khist=[0u64;16];
        for k in 0..16{
            let Some(n)=slow.counters[14+k].checked_sub(hist.counters[14+k])
                else{return self.invalid(now)};
            khist[k]=n;
        }
        if khist.iter().all(|&n|n==0){return self.invalid(now)}
        let pf=(f.missing as f64)/(f.observed as f64);
        let ps=(s.missing as f64)/(s.observed as f64);
        let margin=(1.64*(ps*(1.0-ps)/(s.observed as f64)).max(0.0).sqrt()).min(0.005);
        let p=(pf.max(ps)+margin).min(1.0);
        let mut target=6u8;
        for profile in 0..7u8{
            if guarded(&khist,profile,p,s.sent)<=0.001{
                target=profile;break
            }
        }
        if self.aggressive{target=(target+1).min(6)}
        if target>self.profile{
            self.clear_down();
            self.rising=self.rising.saturating_add(1);
            if self.rising>=2{self.rising=0;return self.propose(target)}
            return None
        }
        self.rising=0;
        if target<self.profile&&self.profile>0&&
            guarded(&khist,self.profile-1,p,s.sent)<=0.0005{
            if self.down_since.is_none()||
                self.down_last_valid.is_some_and(|v|now.saturating_sub(v)>6*S){
                self.clear_down();self.down_since=Some(now);
            }
            self.down_last_valid=Some(now);
            self.down_sources=self.down_sources.saturating_add(f.observed);
            self.down_windows=self.down_windows.saturating_add(1).min(5);
            if self.down_since.is_some_and(|at|now.saturating_sub(at)>=30*S)&&
                self.down_windows>=5&&self.down_sources>=4096&&
                self.last_down.is_none_or(|at|now.saturating_sub(at)>=30*S){
                self.clear_down();
                return self.propose(self.profile-1);
            }
        }else{self.clear_down()}
        None
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    #[test]
    fn no_mature_k_or_receipts_no_auto_grade_and_no_false_success(){
        let mut a=NativeAutoActor::new(5,1,false,0);
        for tick in 1..=120{
            let now=tick*2*S;
            assert_eq!(a.evaluate(now,[0;30]),None);
            assert_eq!(a.revision(),1);
        }
    }
    #[test]
    fn genuine_2s_8s_mature_m2_down_one_rung_only_after_30s_and_4096(){
        let mut actor=NativeAutoActor::new(5,1,false,0);
        let mut counters=[0u64;30];
        let mut changed=None;
        for tick in 1..=80u64{
            // 600 true original sources each 2s, matching closed k=1 blocks,
            // complete 2s/8s mature confirmed observations, genuine receipts.
            for i in [0,1,5,6,14]{counters[i]+=600}
            counters[10]+=1;
            counters[12]+=20_000_000;
            counters[13]+=1;
            let now=tick*2*S;
            if let Some(intent)=actor.evaluate(now,counters){
                assert_eq!(intent.profile,4);
                assert_eq!(intent.revision,2);
                actor.commit(intent,now);
                changed=Some(now);
                break
            }
        }
        let at=changed.expect("valid low-loss proof must downgrade by 120s");
        assert!(at>=46*S && at<=120*S);
        assert_eq!(actor.profile(),4);
    }
    #[test]
    fn two_real_high_loss_m2_windows_raise_without_fabricating_zero_loss(){
        let mut actor=NativeAutoActor::new(0,1,false,0);
        let mut counters=[0u64;30];
        let mut raised=None;
        for tick in 1..=80u64{
            for i in [0,5,14]{counters[i]+=600}
            for i in [1,6]{counters[i]+=510}
            for i in [2,7]{counters[i]+=90}
            counters[10]+=1;
            counters[12]+=20_000_000;
            counters[13]+=1;
            if let Some(intent)=actor.evaluate(tick*2*S,counters){
                assert!(intent.profile>0);
                raised=Some(intent);
                break
            }
        }
        assert!(raised.is_some());
    }
    #[test]
    fn host_capacity_or_missing_actual_k_refuses_all_auto_changes(){
        let mut actor=NativeAutoActor::new(5,1,false,0);
        let mut counters=[0u64;30];
        for tick in 1..=80u64{
            for i in [0,1,5,6]{counters[i]+=600}
            counters[10]+=1;counters[11]+=1;
            counters[12]+=20_000_000;counters[13]+=1;
            assert!(actor.evaluate(tick*2*S,counters).is_none());
        }
        assert_eq!(actor.profile(),5);
        assert_eq!(actor.revision(),1);
    }
    #[test]
    fn exact_rho_levels_and_conservative_residual_are_ordered(){
        assert_eq!([parity(0,16),parity(1,16),parity(2,16),
            parity(3,16),parity(4,16),parity(5,16),parity(6,16)],
            [2,4,6,8,12,16,20]);
        for p in [0.01,0.05,0.15,0.3]{
            let h=[1u64;16];
            for g in 1..=6{assert!(guarded(&h,g,p,136.0 as u64)<=
                guarded(&h,g-1,p,136.0 as u64)+0.00000001)}
        }
    }
}

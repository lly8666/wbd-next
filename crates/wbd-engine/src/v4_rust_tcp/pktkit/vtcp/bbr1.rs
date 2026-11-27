//! Experimental BBRv1-style controller, independently implemented from
//! Cardwell et al., "BBR: Congestion-Based Congestion Control" (2016) and
//! public Linux BBRv1 behavior. Byte units; existing TCP delivery samples,
//! RACK/SACK, pacing and owner. Not a verbatim Linux port. The v1 token-bucket
//! policer estimator and packet quantization are implemented below; the
//! kernel's skb EDT/TSO queue ownership is not replicated.
use super::congestion::{Ack, CongestionController, Lost, initial_window};
use crate::v4_rust_tcp::pktkit::time::Instant;
use std::{collections::VecDeque, time::Duration};

const HIGH: f64 = 739.0 / 256.0;
const CYCLE: [f64;8] = [1.25,0.75,1.,1.,1.,1.,1.,1.];
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Mode { Startup, Drain, ProbeBw, ProbeRtt }

pub struct Bbr1 {
    mss:u32, init:u32, cwnd:u32, rate:u64,
    mode:Mode, cycle:usize, cycle_at:Instant,
    round:u64, next_round:u64, bw_samples:VecDeque<(u64,u64)>, bw:u64,
    full_bw:u64, full_rounds:u8, full:bool,
    min_rtt:Option<Duration>, min_stamp:Instant, seen_rtt:bool,
    probe_until:Option<Instant>, probe_round:u64, probe_saved:u32,
    recovery:bool, conserve_until:Option<u64>, enter_recovery:bool, prior_cwnd:u32,
    idle_restart:bool, mark_app:bool,
    ack_epoch:Instant, ack_bytes:u64, extra:[u64;2], extra_slot:usize, extra_round:u64,
    lt_start:Option<(Instant,u64,u64,u64)>, lt_previous:u64,
    lt_bw:u64, lt_since:u64, total_lost:u64,
}
impl Bbr1 {
    pub fn new(mss:u32,now:Instant)->Self{
        let mss=mss.max(1); let init=initial_window(mss);
        Self{mss,init,cwnd:init,rate:(HIGH*f64::from(init)*1000.) as u64,
            mode:Mode::Startup,cycle:0,cycle_at:now,round:0,next_round:0,
            bw_samples:VecDeque::with_capacity(10),bw:0,full_bw:0,full_rounds:0,full:false,
            min_rtt:None,min_stamp:now,seen_rtt:false,probe_until:None,probe_round:0,probe_saved:0,
            recovery:false,conserve_until:None,enter_recovery:false,prior_cwnd:0,
            idle_restart:false,mark_app:false,ack_epoch:now,ack_bytes:0,
            extra:[0;2],extra_slot:0,extra_round:0,
            lt_start:None,lt_previous:0,lt_bw:0,lt_since:0,total_lost:0}
    }
    fn min_pipe(&self)->u32{4*self.mss}
    fn rtt(&self)->Duration{self.min_rtt.unwrap_or(Duration::from_millis(1))}
    fn model_bw(&self)->u64{if self.lt_bw!=0{self.lt_bw}else{self.bw}}
    fn bdp_for(&self,bw:u64,gain:f64)->u32{
        if bw==0||self.min_rtt.is_none(){return self.init}
        let bytes=(bw as f64*self.rtt().as_secs_f64()*gain).ceil() as u64;
        (bytes.div_ceil(u64::from(self.mss))*u64::from(self.mss)).min(u64::from(u32::MAX)) as u32
    }
    fn bdp(&self,gain:f64)->u32{self.bdp_for(self.model_bw(),gain)}
    // Model allowance, not a claim that the carrier implements TSO.
    fn tso_goal(&self)->u32 {
        let min=if self.rate<150_000{1}else{2};
        ((self.rate>>10).min(65_000)/u64::from(self.mss)).clamp(min,127) as u32
    }
    fn quantize(&self,bytes:u32)->u32 {
        let segs=bytes.div_ceil(self.mss).saturating_add(3*self.tso_goal());
        let segs=segs.saturating_add(1)&!1;
        segs.saturating_add(if self.mode==Mode::ProbeBw&&self.cycle==0{2}else{0}).saturating_mul(self.mss)
    }
    fn inflight_target(&self,gain:f64)->u32{self.quantize(self.bdp(gain))}
    fn gains(&self)->(f64,f64){match self.mode{
        Mode::Startup=>(HIGH,HIGH),Mode::Drain=>(88./256.,HIGH),
        Mode::ProbeBw=>(if self.lt_bw!=0{1.}else{CYCLE[self.cycle]},2.),Mode::ProbeRtt=>(1.,1.),
    }}
    fn probe_bw(&mut self,now:Instant){
        self.mode=Mode::ProbeBw;
        // Deterministic initial neutral phase for the single-flow experiment.
        self.cycle=2;self.cycle_at=now;
    }
    fn update_bw(&mut self,a:&Ack)->bool{
        let Some(s)=a.rs else{return false};
        let start=s.prior_delivered>=self.next_round;
        if start{self.round+=1;self.next_round=a.delivered;}
        if s.delivery_rate>0&&(!s.is_app_limited||s.delivery_rate>=self.bw){
            while self.bw_samples.front().is_some_and(|&(r,_)|self.round.saturating_sub(r)>=10){self.bw_samples.pop_front();}
            while self.bw_samples.back().is_some_and(|&(_,b)|b<=s.delivery_rate){self.bw_samples.pop_back();}
            // A weaker sample in the same round cannot outlive its maximum.
            if self.bw_samples.back().is_none_or(|&(r,_)|r!=self.round){
                self.bw_samples.push_back((self.round,s.delivery_rate));
            }
            self.bw=self.bw_samples.front().map_or(s.delivery_rate,|&(_,b)|b);
        }
        if start&&!self.full&&!s.is_app_limited&&self.bw>0 {
            if self.bw as f64>=1.25*self.full_bw as f64{
                self.full_bw=self.bw;self.full_rounds=0;
            }else{
                self.full_rounds+=1;
                if self.full_rounds>=3{self.full=true;}
            }
        }
        start
    }
    fn reset_lt(&mut self){self.lt_start=None;self.lt_previous=0;self.lt_bw=0;self.lt_since=0;}
    fn sample_lt(&mut self,a:&Ack,round_start:bool){
        if self.lt_bw!=0 {
            if self.mode==Mode::ProbeBw && round_start && self.round.saturating_sub(self.lt_since)>=48 {
                self.reset_lt();self.probe_bw(a.now);
            }
            return;
        }
        let Some(rs)=a.rs else{return};
        if rs.is_app_limited{self.reset_lt();return;}
        if self.lt_start.is_none(){
            if a.newly_lost==0{return;}
            self.lt_start=Some((a.now,a.delivered,self.total_lost,self.round));return;
        }
        let (start,delivered,lost,round)=self.lt_start.unwrap();
        let rounds=self.round.saturating_sub(round);
        if rounds<4{return;}
        if rounds>16{self.reset_lt();return;}
        if a.newly_lost==0{return;}
        let delivered=a.delivered.saturating_sub(delivered);
        let lost=self.total_lost.saturating_sub(lost);
        if delivered==0 || u128::from(lost)*256 < u128::from(delivered)*50{return;}
        let dt=a.now.saturating_duration_since(start);
        if dt<Duration::from_millis(1){return;}
        let bw=(u128::from(delivered)*1_000_000_000/dt.as_nanos()).min(u64::MAX as u128) as u64;
        let prior=self.lt_previous;
        if prior!=0 && (u128::from(bw.abs_diff(prior))*8<=u128::from(prior)||bw.abs_diff(prior)<=500){
            self.lt_bw=prior/2+bw/2;self.lt_since=self.round;
        }else{self.lt_previous=bw;self.lt_start=Some((a.now,a.delivered,self.total_lost,self.round));}
    }
    fn ack_aggregation(&mut self,a:&Ack){
        if a.newly_acked==0{return}
        if self.round.saturating_sub(self.extra_round)>=5{
            self.extra_round=self.round;self.extra_slot^=1;self.extra[self.extra_slot]=0;
        }
        let expected=(self.model_bw() as f64*a.now.saturating_duration_since(self.ack_epoch).as_secs_f64()) as u64;
        if self.ack_bytes<=expected{self.ack_epoch=a.now;self.ack_bytes=0;}
        self.ack_bytes=self.ack_bytes.saturating_add(u64::from(a.newly_acked));
        let expected=(self.model_bw() as f64*a.now.saturating_duration_since(self.ack_epoch).as_secs_f64()) as u64;
        let excess=self.ack_bytes.saturating_sub(expected).min(u64::from(self.cwnd));
        self.extra[self.extra_slot]=self.extra[self.extra_slot].max(excess);
    }
    fn update_mode(&mut self,a:&Ack){
        if self.mode==Mode::Startup&&self.full{self.mode=Mode::Drain;}
        if self.mode==Mode::Drain&&a.inflight<=self.inflight_target(1.){self.probe_bw(a.now);}
        if self.mode==Mode::ProbeBw{
            let elapsed=a.now.saturating_duration_since(self.cycle_at)>=self.rtt();
            let gain=if self.lt_bw!=0{1.}else{CYCLE[self.cycle]};
            let prior=a.flight;
            let target=self.quantize(self.bdp_for(self.bw,gain));
            let next=if gain>1.{elapsed&&(a.newly_lost>0||prior>=target)}
                else if gain<1.{elapsed||prior<=self.quantize(self.bdp_for(self.bw,1.))}else{elapsed};
            if next{self.cycle=(self.cycle+1)%8;self.cycle_at=a.now;}
        }
        let expired=a.now.saturating_duration_since(self.min_stamp)>=Duration::from_secs(10);
        if let Some(r)=a.newest_rtt.or(a.rtt).filter(|r|!r.is_zero()){
            if !self.seen_rtt{
                self.seen_rtt=true;
                self.rate=(HIGH*f64::from(self.cwnd)/r.as_secs_f64()) as u64;
            }
            if expired||self.min_rtt.is_none_or(|old|r<=old){self.min_rtt=Some(r);self.min_stamp=a.now;}
        }
        if expired&&!self.idle_restart&&self.mode!=Mode::ProbeRtt{
            self.probe_saved=self.cwnd;self.mode=Mode::ProbeRtt;self.probe_until=None;
        }
        if self.mode==Mode::ProbeRtt{
            self.mark_app=true;
            if self.probe_until.is_none()&&a.inflight<=self.min_pipe(){
                self.probe_until=Some(a.now+Duration::from_millis(200));self.probe_round=self.round+1;
            }
            if self.probe_until.is_some_and(|d|a.now>=d)&&self.round>=self.probe_round{
                self.min_stamp=a.now;self.cwnd=self.cwnd.max(self.probe_saved);
                if self.full{self.probe_bw(a.now)}else{self.mode=Mode::Startup}
            }
        }
        if a.newly_acked>0{self.idle_restart=false;}
    }
    pub(crate) fn probe(&self,leg:&str,id:u64,wall_ns:u128){
        let (pg,cg)=self.gains();
        eprintln!("WBD_M0_BBR1 wall_ns={} leg={} id={} phase={:?} cycle={} bw={} min_rtt={:?} round={} full_bw={} full_bw_reached={} pacing_gain={} cwnd_gain={} cwnd={} pacing_rate={} recovery={} conservation={} extra_acked={} lt_bw={} lt_previous={} tso_goal={}",
            wall_ns,leg,id,self.mode,self.cycle,self.bw,self.min_rtt,self.round,self.full_bw,self.full,pg,cg,self.cwnd,self.rate,self.recovery,self.conserve_until.is_some(),self.extra[0].max(self.extra[1]),self.lt_bw,self.lt_previous,self.tso_goal());
    }
}
impl CongestionController for Bbr1{
    fn name(&self)->&'static str{"bbr1"}
    fn model_based(&self)->bool{true}
    fn as_bbr1(&self)->Option<&Bbr1>{Some(self)}
    fn on_ack(&mut self,a:&Ack){
        let round_start=self.update_bw(a);self.sample_lt(a,round_start);self.ack_aggregation(a);self.update_mode(a);
        let (pg,cg)=self.gains();
        if self.bw>0{
            let rate=(self.model_bw() as f64*pg*0.99) as u64;
            if self.full||rate>self.rate||self.mode==Mode::ProbeRtt{self.rate=rate.max(1);}
        }
        let mut cwnd=self.cwnd.saturating_sub(a.newly_lost).max(self.mss);
        if std::mem::take(&mut self.enter_recovery){
            cwnd=a.inflight.saturating_add(a.newly_acked.max(self.mss));
            self.conserve_until=Some(self.round+1);
        }
        if self.conserve_until.is_some_and(|r|self.round>=r){self.conserve_until=None;}
        if self.conserve_until.is_some(){
            cwnd=cwnd.max(a.inflight.saturating_add(a.newly_acked));
        }else if a.newly_acked>0{
            let extra=if self.full{self.extra[0].max(self.extra[1]).min(self.model_bw()/10)}else{0};
            let target=self.quantize(self.bdp(cg).saturating_add(extra.min(u64::from(u32::MAX)) as u32)).max(self.min_pipe());
            if self.full{cwnd=cwnd.saturating_add(a.newly_acked).min(target);}
            else if cwnd<target||a.delivered<u64::from(self.init){cwnd=cwnd.saturating_add(a.newly_acked);}
        }
        self.cwnd=cwnd.max(self.min_pipe());
        if self.mode==Mode::ProbeRtt{self.cwnd=self.cwnd.min(self.min_pipe());}
    }
    fn on_lost(&mut self,lost:&Lost){self.total_lost=lost.total_lost;}
    fn on_loss(&mut self,_flight:u32){
        self.prior_cwnd=self.cwnd.max(self.prior_cwnd);self.recovery=true;self.enter_recovery=true;
    }
    fn on_retransmit_timeout(&mut self,_flight:u32,_repeated:bool){
        self.prior_cwnd=self.cwnd.max(self.prior_cwnd);self.recovery=true;
        self.enter_recovery=false;self.conserve_until=None;self.cwnd=self.mss;self.full_bw=0;self.full_rounds=0;self.reset_lt();
    }
    fn on_handshake_loss(&mut self){self.cwnd=self.mss;}
    fn on_recovery_exit(&mut self){
        self.recovery=false;self.enter_recovery=false;self.conserve_until=None;
        self.cwnd=self.cwnd.max(self.prior_cwnd);self.prior_cwnd=0;
    }
    fn on_transmit(&mut self,now:Instant,idle:bool){
        if idle{self.idle_restart=true;self.ack_epoch=now;self.ack_bytes=0;
            if self.mode==Mode::ProbeBw&&self.bw>0{self.rate=(self.model_bw() as f64*0.99) as u64;}
        }
    }
    fn take_app_limited(&mut self)->bool{std::mem::take(&mut self.mark_app)}
    fn pacing_rate(&self)->Option<u64>{Some(self.rate.max(1))}
    fn set_mss(&mut self,mss:u32){self.mss=mss.max(1);}
    fn set_cwnd(&mut self,cwnd:u32){self.cwnd=cwnd.max(self.mss);}
    fn undo(&mut self,cwnd:u32,_ssthresh:u32){self.on_recovery_exit();self.cwnd=self.cwnd.max(cwnd);self.full_bw=0;self.full_rounds=0;}
    fn restart(&mut self,cwnd:u32,_ssthresh:u32){self.set_cwnd(cwnd);}
    fn cwnd(&self)->u32{self.cwnd}
    fn ssthresh(&self)->u32{u32::MAX}
}

#[cfg(test)]
mod tests{
    use super::*;
    use super::super::rate::RateSample;
    fn feed(b:&mut Bbr1,now:Instant,prior:u64,rate:u64,lost:u32,app:bool){
        let bytes=(rate/10) as u32;
        b.on_ack(&Ack{now,rs:Some(RateSample{delivery_rate:rate,prior_delivered:prior,
            delivered:u64::from(bytes),interval:Duration::from_millis(100),is_app_limited:app,
            tx_in_flight:bytes,..Default::default()}),newly_acked:bytes,newly_lost:lost,
            delivered:prior+u64::from(bytes),newest_rtt:Some(Duration::from_millis(100)),
            ..Ack::of(now,bytes,bytes)});
    }
    #[test]
    fn v1_plateau_enters_probe_and_does_not_bound_bw_by_random_loss(){
        let now=Instant::now();let mut b=Bbr1::new(1000,now);
        let rate=1_000_000;let mut prior=0;
        for i in 1..=20{
            feed(&mut b,now+Duration::from_millis(i*100),prior,rate,5000,false);
            prior+=rate/10;
        }
        assert!(b.full);
        assert_eq!(b.mode,Mode::ProbeBw);
        assert_eq!(b.bw,rate);
        assert!(b.cwnd()>=100_000);
        assert!(b.pacing_rate().unwrap()>=rate*3/4-10_000);
    }
    #[test]
    fn v1_policer_uses_two_consistent_loss_intervals_then_expires(){
        let now=Instant::now();let mut b=Bbr1::new(1000,now);
        b.mode=Mode::ProbeBw;
        let mut a=Ack::of(now,100_000,100_000);
        a.rs=Some(RateSample{delivery_rate:1_000_000,..Default::default()});
        a.newly_lost=30_000;
        b.sample_lt(&a,true);
        for i in 1..=8 {
            b.round=i; b.total_lost=i*30_000;
            a.now=now+Duration::from_millis(i*100);
            a.delivered=i*100_000;
            b.sample_lt(&a,true);
        }
        assert_eq!(b.lt_bw,1_000_000);
        assert_eq!(b.gains().0,1.);
        b.round+=48;b.sample_lt(&a,true);assert_eq!(b.lt_bw,0);
    }

    #[test]
    fn v1_recovery_is_transient_and_app_limited_sample_not_capacity(){
        let now=Instant::now();let mut b=Bbr1::new(1000,now);
        feed(&mut b,now+Duration::from_millis(100),0,1_000_000,0,false);
        feed(&mut b,now+Duration::from_millis(200),100_000,100_000,0,true);
        assert_eq!(b.bw,1_000_000);
        b.set_cwnd(200_000);b.on_loss(180_000);assert!(b.enter_recovery);
        b.set_cwnd(40_000);b.on_recovery_exit();assert_eq!(b.cwnd(),200_000);
        assert!(!b.recovery);
    }
}

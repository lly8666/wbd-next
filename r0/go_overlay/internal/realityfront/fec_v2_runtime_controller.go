package realityfront

// M0 original-Go control-plane scheduler. It does not grant Rust authority:
// the caller must supply an exact already-authenticated epoch and a backend
// that checks the same epoch when staging a revision or reading an ACK.
// Merely constructing this object performs NO network IO and cannot enable
// FEC2 in the ordinary OFF build.
import (
    "errors"
    "sync"
    "time"
)

var errFecV2RuntimeStopped = errors.New("fec v2: original Go controller stopped")
const fecV2RuntimeCadence = 2*time.Second

type fecV2RuntimeBackend interface {
    // Observe must never synthesize a first-sent loss denominator. An
    // unavailable/insufficient source returns UNKNOWN or an error.
    Observe(epoch [16]byte,client string,direction FecV2Direction,now time.Duration)(FecV2Snapshot,error)
    // Stage is the already-verified original owner control write; its own
    // generation/epoch guard must reject Stop and stale identity.
    Stage(epoch [16]byte,intent FecV2Intent) error
    // Readback MUST reflect original Rust applied policy, never requested.
    Readback(epoch [16]byte,client string,direction FecV2Direction)(FecV2Ack,error)
}

// One controller per authenticated client+direction+epoch. No process-global
// profile, stale cross-client ACK, idle SetTxFec or Go per-packet helpers.
type fecV2ControlRuntime struct {
    mu sync.Mutex
    cfg FecV2Config
    epoch [16]byte
    backend fecV2RuntimeBackend
    state FecV2State
    started bool
    stopped bool
    stop chan struct{}
    done chan struct{}
    lastError error
}

func newFecV2ControlRuntime(
    cfg FecV2Config,epoch [16]byte,backend fecV2RuntimeBackend,
)(*fecV2ControlRuntime,error){
    if err:=cfg.validate();err!=nil{return nil,err}
    if cfg.Mode!=FecV2Auto||cfg.Transport!=FecV2Normal||
        epoch==[16]byte{}||backend==nil{return nil,ErrFecV2Scope}
    return &fecV2ControlRuntime{
        cfg:cfg,epoch:epoch,backend:backend,
        stop:make(chan struct{}),done:make(chan struct{}),
    },nil
}

// Tick is serialized against Stop; the backend is called with NO Rust lock
// held by Go. A failed stage never marks an unapplied revision requested.
// A stale/out-of-scope ACK never overwrites the current applied snapshot.
func (r *fecV2ControlRuntime) Tick(now time.Duration) error {
    r.mu.Lock()
    defer r.mu.Unlock()
    if r.stopped{return errFecV2RuntimeStopped}
    if now<0{return errFecV2Policy}
    if r.state.Initialized{
        ack,err:=r.backend.Readback(r.epoch,r.cfg.Client,r.cfg.Direction)
        if err==nil{
            applied,_,err:=FecV2Apply(r.state,ack)
            if err!=nil{return err}
            r.state=applied
        }
    }
    snap,err:=r.backend.Observe(r.epoch,r.cfg.Client,r.cfg.Direction,now)
    if err!=nil{
        // This is UNKNOWN, not a fabricated no-loss window.
        snap=FecV2Snapshot{
            Client:r.cfg.Client,Direction:r.cfg.Direction,
            At:now,Validity:FecV2Unknown,
        }
    }
    next,intent,err:=FecV2Step(r.cfg,r.state,snap,now)
    if err!=nil{return err}
    if intent.Send{
        if intent.Client!=r.cfg.Client||intent.Direction!=r.cfg.Direction||
            intent.Revision==0||!intent.Profile.Valid(){
            return ErrFecV2Scope
        }
        if err:=r.backend.Stage(r.epoch,intent);err!=nil{return err}
    }
    r.state=next
    return nil
}

// Start schedules the real two-second cadence, not a per-packet callback.
// Failed ticks do not silently advance a requested revision. Close joins
// this worker; no late SetTxFec is issued after Close returns.
func (r *fecV2ControlRuntime) Start() error {
    r.mu.Lock()
    defer r.mu.Unlock()
    if r.started||r.stopped{return errFecV2RuntimeStopped}
    r.started=true
    go func(){
        defer close(r.done)
        ticker:=time.NewTicker(fecV2RuntimeCadence)
        defer ticker.Stop()
        start:=time.Now()
        for {
            select{
            case <-r.stop:return
            case <-ticker.C:
                err:=r.Tick(time.Since(start))
                r.mu.Lock()
                r.lastError=err
                r.mu.Unlock()
            }
        }
    }()
    return nil
}

func (r *fecV2ControlRuntime) Stop() {
    r.mu.Lock()
    if !r.stopped{
        r.stopped=true
        close(r.stop)
    }
    done:=r.done
    started:=r.started
    r.mu.Unlock()
    if started{<-done}
}

func (r *fecV2ControlRuntime) Snapshot()(FecV2State,error){
    r.mu.Lock()
    defer r.mu.Unlock()
    return r.state,r.lastError
}

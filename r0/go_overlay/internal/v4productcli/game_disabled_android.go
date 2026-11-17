//go:build android && cgo && wbd_v4_embedded_go && !wbd_v4_fec2_product

package v4productcli

import (
    "context"
    "errors"
    "fmt"
    "log"
    "time"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
    "github.com/lly8666/wobuzhidao/internal/logicaltunnel"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
)

// The source-locked original Game4 cold candidate sentinel remains typed
// solely for the unchanged shared physical-path supervisor. No unsupported
// Game candidate or second Go M4 worker can be created in this edition.
var errOriginalGameLaneColdCandidate=errors.New(
    "new Game4 cold TLS candidate not installed",
)

// Exact original protected Normal/Off cold final-ACK retransmit guard from
// game_linux.go: it is needed by runClient (Normal too). The detached
// original Go FakeTCP association only replays its verified final ACK;
// no new record kind, credentials, packet engine, tunnel or repair lane.
func repeatOriginalDetachedTLSFinalACK(
    ctx context.Context,assocs ...*faketcp.ClientAssociation,
){
    go func(){
        previous:=time.Duration(0)
        emitted:=0
        for _,delay:=range [...]time.Duration{
            80*time.Millisecond,240*time.Millisecond,560*time.Millisecond,
            1120*time.Millisecond,2240*time.Millisecond,4480*time.Millisecond,
        }{
            timer:=time.NewTimer(delay-previous)
            select{
            case <-ctx.Done():
                timer.Stop()
                return
            case <-timer.C:
            }
            previous=delay
            for _,a:=range assocs{
                if a==nil||a.State()!=faketcp.ClientAssociationDetached{continue}
                if err:=a.RepeatDetachedBootstrapACK();err==nil{emitted++}
            }
        }
        log.Printf(
            "V4_PUBLIC_TLS_REPLY_ACK_COLD_GUARD role=client lanes=%d duplicate_pure_acks=%d window_ms=4480 new_wire_fields=0",
            len(assocs),emitted,
        )
    }()
}

// Game2/4 cannot run without the original real authenticated M4 Game
// product. These functions intentionally fail closed and never attempt
// a partial Go-only TLS or fake FEC/Game native owner.
func runGame(
    _ context.Context,c config,_ uint32,_ *ownedTun,
    _ *logicaltunnel.LeaseRegistry,_ *realityfront.V4EpochStore,
    _ *bool,
)error{
    return fmt.Errorf(
        "original Go V4 Game%d native M4 product not compiled",c.gameLanes,
    )
}

// Preserve the full existing 7-argument path-supervisor signature while
// refusing to start any Game lane, including a single-lane rotation.
func runGameClientGeneration(
    _ context.Context,c config,_ uint32,_ *ownedTun,
    _ *bool,_ chan<- struct{},_ <-chan originalGameLaneTurn,
)error{
    return fmt.Errorf(
        "original Go V4 Game%d native M4 product not compiled",c.gameLanes,
    )
}

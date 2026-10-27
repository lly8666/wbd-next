package runtimeentry

// PLAN-008: one original Go product flag namespace and an honest readback
// boundary. Rust capability/verified admission remain M0-only. These helpers
// cannot activate a dataplane, and DO NOT mint an applied acknowledgement.
import (
    "errors"
    "flag"
    "fmt"
)

var ErrFEC2ProductUnwired = errors.New("FEC2 product owner unavailable: authenticated native SetTxFec/applied readback is not wired")

// FEC2ProductFlags are backed by the original CLI FlagSet. The same keys
// persist in original JSON and are edited by the original portable WinForms.
type FEC2ProductFlags struct {
    Mode *string
    Profile *string
    AutoPolicy *string
    AutoStartProfile *string
}

func RegisterFEC2ProductFlags(fs *flag.FlagSet) *FEC2ProductFlags {
    return &FEC2ProductFlags{
        Mode: fs.String("fec.mode","off","FEC2: off|fixed|auto; requires authenticated native owner for fixed/auto"),
        Profile: fs.String("fec.profile","strong","FEC2 fixed profile: light|mild|medium|balanced|high|strong|maximum"),
        AutoPolicy: fs.String("fec.auto_policy","normal","FEC2 auto policy: normal|aggressive (Normal lanes only)"),
        AutoStartProfile: fs.String("fec.auto_start_profile","strong","FEC2 normal auto start profile before +1 aggressive offset"),
    }
}
func fec2ValidProfile(s string) bool {
    switch s {
    case "light","mild","medium","balanced","high","strong","maximum": return true
    }
    return false
}
func (p *FEC2ProductFlags) Validate(lanes int) error {
    if p==nil || p.Mode==nil || p.Profile==nil || p.AutoPolicy==nil || p.AutoStartProfile==nil {return errors.New("FEC2 parameter binding missing")}
    if lanes < 1 || lanes > 4 {return errors.New("FEC2 invalid lane count")}
    if !fec2ValidProfile(*p.Profile) || !fec2ValidProfile(*p.AutoStartProfile) {
        return errors.New("fec.profile and fec.auto_start_profile must use one of the seven FEC2 profiles")
    }
    if *p.AutoPolicy!="normal" && *p.AutoPolicy!="aggressive" {
        return errors.New("fec.auto_policy must be normal or aggressive")
    }
    switch *p.Mode {
    case "off":
    case "fixed":
        // Linux's one shared FEC2 seven-profile selector; Game2/4
        // negotiates this in the protected V4 GameFec TLV, while Normal
        // uses the original feature7 TLS/M2 FixedStream after Detach.
    case "auto":
        if lanes>1 {return errors.New("Game auto FEC2 is unsupported")}
    default:
        return errors.New("fec.mode must be off, fixed or auto; legacy parity values are not FEC2 profiles")
    }
    return nil
}

// RuntimeReady requires actual M0 authenticated adapter and real Rust ACK.
// A CLI flag, GUI save, env var, or synthetic status cannot enable FEC2.
func (p *FEC2ProductFlags) RuntimeReady() error {
    if p==nil || p.Mode==nil {return errors.New("FEC2 parameter binding missing")}
    if *p.Mode!="off" {return ErrFEC2ProductUnwired}
    return nil
}

// Snapshot never reports "applied" for an unconnected engine. The M0 owner
// will provide real readback when it wires authenticated client/direction,
// epoch, revision and new-block policy. No status here updates idle clocks.
func (p *FEC2ProductFlags) CheckConfigStatus(dst map[string]string) {
    dst["fec.status"]="disabled"
    dst["fec.applied_profile"]="unknown"
    dst["fec.applied_revision"]="unknown"
    dst["fec.pending_revision"]="none"
    dst["fec.reject_reason"]=""
    if p!=nil && p.Mode!=nil && *p.Mode!="off" {
        dst["fec.status"]="rejected"
        dst["fec.reject_reason"]=ErrFEC2ProductUnwired.Error()
    }
}

// This projection is for display ONLY, not a second controller. Late,
// untrusted, cross-client/direction or old-epoch replies cannot overwrite the
// current requested state. The adapter caller MUST supply an M0-authenticated
// receipt rather than a caller-supplied status string or user-facing flag.
type FEC2Readback struct {
    Client, Direction, Epoch string
    Revision uint64
    Profile string
    State string // pending|applied|rejected, from the verified Rust owner
    Reason string
}
type FEC2Display struct {
    RequestedProfile string
    Client, Direction, Epoch string
    RequestedRevision uint64
    Status string
    AppliedProfile string
    AppliedRevision uint64
    Reason string
}
func ProjectVerifiedFEC2Status(current FEC2Display, verified *FEC2Readback) FEC2Display {
    if verified==nil || current.Client=="" || current.Epoch=="" ||
        verified.Client!=current.Client || verified.Direction!=current.Direction ||
        verified.Epoch!=current.Epoch || verified.Revision!=current.RequestedRevision {
        return current
    }
    switch verified.State {
    case "pending":
        current.Status="pending"
    case "rejected":
        current.Status="rejected"
        current.Reason=verified.Reason
    case "applied":
        if !fec2ValidProfile(verified.Profile) || verified.Profile!=current.RequestedProfile {
            current.Status="rejected"
            current.Reason="FEC2 applied profile mismatches requested policy"
            return current
        }
        current.Status="applied"
        current.AppliedProfile=verified.Profile
        current.AppliedRevision=verified.Revision
        current.Reason=""
    default:
        current.Status="rejected"
        current.Reason=fmt.Sprintf("unsupported authenticated FEC2 readback state")
    }
    return current
}

package runtimeentry

import (
    "errors"

    "github.com/lly8666/wobuzhidao/internal/realityfront"
)

// ErrR0V4DataPlaneUnavailable is a deliberate production boundary: the
// prototype Go TLS V4 handshake exists, but old runtimeowner/datapath cannot
// interpret authenticated V4 receipt/Game/control bundles. Never accept an
// operator-supplied readiness boolean or quietly change V4 to V3.
var ErrR0V4DataPlaneUnavailable = errors.New(
    "runtimeentry: V4 requested but Rust receipt/Game data plane and ABI are not implemented",
)
var ErrR0AdmissionVersion = errors.New("runtimeentry: unsupported requested admission version")

// R0EffectiveClientAdmission is read-only config resolution. Zero preserves
// old direct library callers (including test-only V2); 3 means explicitly
// select V3 and requires a real V3 protected policy.
func R0EffectiveClientAdmission(requested uint16, policy realityfront.AdmissionPolicy) (uint16, error) {
    switch requested {
    case 0:
        if policy.Schema == 0 {
            return realityfront.RecordVersionV2, nil
        }
        if policy.Schema == realityfront.PolicySchemaV3 {
            return realityfront.RecordVersionV3, nil
        }
        return 0, ErrR0AdmissionVersion
    case realityfront.RecordVersionV3:
        if policy.Schema != realityfront.PolicySchemaV3 {
            return 0, ErrR0AdmissionVersion
        }
        if err := policy.SupportedNow(); err != nil {
            return 0, err
        }
        return realityfront.RecordVersionV3, nil
    case realityfront.V4RecordVersion:
        return 0, ErrR0V4DataPlaneUnavailable
    default:
        return 0, ErrR0AdmissionVersion
    }
}

// R0EffectiveServerAdmission retains legacy zero-value server callers.
// Production V3 server callers explicitly choose 3 and RequireV3=true.
func R0EffectiveServerAdmission(requested uint16, requireV3 bool) (uint16, error) {
    switch requested {
    case 0:
        if requireV3 { return realityfront.RecordVersionV3,nil }
        return realityfront.RecordVersionV2,nil
    case realityfront.RecordVersionV3:
        if !requireV3 { return 0,ErrR0AdmissionVersion }
        return realityfront.RecordVersionV3,nil
    case realityfront.V4RecordVersion:
        return 0,ErrR0V4DataPlaneUnavailable
    default:
        return 0,ErrR0AdmissionVersion
    }
}

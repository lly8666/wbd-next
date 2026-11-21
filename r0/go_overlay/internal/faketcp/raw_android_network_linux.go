//go:build linux && !android
package faketcp
import "errors"
// Original Linux AF_PACKET/raw routing already uses the original kernel
// interface binding and route supervision. No Android netid applies.
func (e *RawIPv4Endpoint) BindAndroidNetwork(
    handle uint64,_ string,_ int,_ int,
) error {
    if e==nil||handle!=0{return errors.New("faketcp: Android Network on Linux")}
    return nil
}

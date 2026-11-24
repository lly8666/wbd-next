//go:build !linux

package rootjournal

func PlatformSystemDNSRuleIO()*SystemDNSRuleIO{return nil}

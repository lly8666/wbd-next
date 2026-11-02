//! PLAN027A pure cold V4 MTU calculation. No OS/TLS state or packet-time FFI.
use wbd_codec::path_budget::{FrameBudget,FrameBudgetInput,FecReservation};
use wbd_codec::record_frame::MAX_WIRE_LEN;
use crate::{OK,NULL_ARG,BAD_SIZE,BAD_VERSION,UNSUPPORTED};

pub const MTU_BUDGET_ABI_VERSION: u32 = 1;
/// All sizes are complete IPv4 packets or complete encrypted records, never L2.
#[repr(C)]
#[derive(Clone,Copy,Debug)]
pub struct WbdV4MTUBudgetInputV1 {
    pub version: u32,
    pub struct_size: u32,
    pub configured_outer_ip_mtu: u32,
    /// Zero when unknown; otherwise physical egress IP MTU (not TUN).
    pub physical_outer_ip_mtu: u32,
    /// Raw SYN MSS; zero uses current conservative 536 fallback.
    pub peer_advertised_mss: u32,
    /// Complete wire record; zero = automatic cold offer.
    pub agreed_record_wire_cap: u32,
    pub ipv4_header_bytes: u32,
    pub tcp_data_header_bytes: u32,
    /// 0 Normal, 1 FEC2 Fixed/Auto, 2 Game, 3 Game+FEC2.
    pub mode: u32,
}
#[repr(C)]
#[derive(Clone,Copy,Debug,Default)]
pub struct WbdV4MTUBudgetOutputV1 {
    pub version: u32,
    pub struct_size: u32,
    pub effective_outer_ip_ceiling: u32,
    /// Initial SYN MSS ceiling with minimal 20+20 headers.
    pub local_syn_advertised_mss: u32,
    pub record_wire_cap: u32,
    pub record_payload_cap: u32,
    pub single_inner_ip_cap: u32,
    /// Mathematical LINK fragment capacity; supported capability is Normal/off only.
    pub link_fragment_payload_cap: u32,
}

fn derive(i:WbdV4MTUBudgetInputV1)->Result<WbdV4MTUBudgetOutputV1,i32>{
    let fec=match i.mode {
        0|2=>FecReservation::FixedOff,
        1|3=>FecReservation::V3Fec2Adaptive,
        _=>return Err(UNSUPPORTED),
    };
    let peer=if i.peer_advertised_mss==0 {None}
        else {Some(u16::try_from(i.peer_advertised_mss).map_err(|_|UNSUPPORTED)?)};
    let b=FrameBudget::derive(FrameBudgetInput {
        connection_mtu:i.configured_outer_ip_mtu as usize,
        local_packet_mtu:i.physical_outer_ip_mtu as usize,
        ipv4_header_len:i.ipv4_header_bytes as usize,
        tcp_header_len:i.tcp_data_header_bytes as usize,
        peer_mss:peer,
        record_wire_limit:if i.agreed_record_wire_cap==0 {MAX_WIRE_LEN}
            else {i.agreed_record_wire_cap as usize},
        fec,game:matches!(i.mode,2|3),
    }).map_err(|_|UNSUPPORTED)?;
    let syn_mss=b.effective_packet_mtu.checked_sub(40).ok_or(UNSUPPORTED)?;
    Ok(WbdV4MTUBudgetOutputV1 {
        version:MTU_BUDGET_ABI_VERSION,
        struct_size:std::mem::size_of::<WbdV4MTUBudgetOutputV1>() as u32,
        effective_outer_ip_ceiling:b.effective_packet_mtu as u32,
        local_syn_advertised_mss:syn_mss as u32,
        record_wire_cap:b.record_wire_mtu as u32,
        record_payload_cap:b.record_payload_mtu as u32,
        single_inner_ip_cap:b.single_business_payload_mtu as u32,
        link_fragment_payload_cap:b.link_fragment_payload_mtu as u32,
    })
}
/// Version and sizes are checked before any caller data is consumed.
/// No live owner is touched; Go invokes this before TLS and after agreement.
#[no_mangle]
pub unsafe extern "C" fn wbd_m0_v4_mtu_budget_v1(
    input:*const WbdV4MTUBudgetInputV1,input_size:u32,
    output:*mut WbdV4MTUBudgetOutputV1,output_size:u32
)->i32{
    if input.is_null()||output.is_null(){return NULL_ARG}
    if input_size!=std::mem::size_of::<WbdV4MTUBudgetInputV1>() as u32||
        output_size!=std::mem::size_of::<WbdV4MTUBudgetOutputV1>() as u32 {
        return BAD_SIZE
    }
    let i=unsafe{input.read()};
    if i.version!=MTU_BUDGET_ABI_VERSION||i.struct_size!=input_size {
        return BAD_VERSION
    }
    match derive(i) {
        Ok(b)=>{unsafe{output.write(b)};OK},
        Err(e)=>e,
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn input(mode:u32)->WbdV4MTUBudgetInputV1 {
        WbdV4MTUBudgetInputV1 {
            version:1,struct_size:36,configured_outer_ip_mtu:1500,
            physical_outer_ip_mtu:1500,peer_advertised_mss:1460,
            agreed_record_wire_cap:0,ipv4_header_bytes:20,
            tcp_data_header_bytes:20,mode,
        }
    }
    #[test]
    fn cold_ffi_golden_mode_mss_and_version() {
        for (mode,want) in [(0,1429),(1,1415),(2,1413),(3,1398)] {
            let b=derive(input(mode)).unwrap();
            assert_eq!((b.record_wire_cap,b.single_inner_ip_cap),(1460,want));
            assert_eq!(b.local_syn_advertised_mss,1460);
        }
        let mut i=input(0);i.peer_advertised_mss=1200;i.tcp_data_header_bytes=32;
        assert_eq!(derive(i).unwrap().single_inner_ip_cap,1157);
        i.mode=3;
        assert_eq!(derive(i).unwrap().single_inner_ip_cap,1126);
        let mut output=WbdV4MTUBudgetOutputV1::default();
        i=input(3);i.version=2;
        assert_eq!(unsafe{wbd_m0_v4_mtu_budget_v1(&i,36,&mut output,32)},BAD_VERSION);
        i.version=1;
        assert_eq!(unsafe{wbd_m0_v4_mtu_budget_v1(&i,32,&mut output,32)},BAD_SIZE);
        assert_eq!(unsafe{wbd_m0_v4_mtu_budget_v1(&i,36,&mut output,32)},OK);
        assert_eq!(output.single_inner_ip_cap,1398);
    }
}

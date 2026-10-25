//! Isolated, deliberately INSECURE LAN visual-obfuscation experiment.
//! Only the 5-byte framing resembles a TLS application_data record.
//! NO TLS cryptography, integrity, replay defence, authentication, or negotiation.
//! Do not use this as a production WBD record or after a real bootstrap without
//! separately designing and reviewing a new authenticated capability.
#![forbid(unsafe_code)]
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;
use std::time::Duration;

const MAX_TLS_BODY: usize = (1 << 14) + 256;
const OVERHEAD: usize = 5 + 8 + 2; // TLS-like header, clear experiment PN, masked payload length
const DEMO_SEED: u64 = 0x74ba_be32_9afe_5b13; // publicly known non-secret test fixture

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Mode { FixedXor, RollingXor }

fn ipv4_packet_ok(packet: &[u8]) -> bool {
    if packet.len() < 20 || packet.len() > u16::MAX as usize || packet[0] >> 4 != 4 { return false; }
    let ihl = (packet[0] & 15) as usize * 4;
    ihl >= 20 && ihl <= packet.len()
        && usize::from(u16::from_be_bytes([packet[2], packet[3]])) == packet.len()
}

fn mix64(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9e37_79b9_7f4a_7c15);
    x = (x ^ (x >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    x ^ (x >> 31)
}

fn mask(bytes: &mut [u8], mode: Mode, seed: u64, pn: u64) {
    match mode {
        Mode::FixedXor => bytes.iter_mut().for_each(|b| *b ^= 0xa5),
        Mode::RollingXor => {
            // Non-cryptographic PRNG; known plaintext reveals this stream.
            // Packet-local PN input prevents the simple repeated-body test.
            let mut state = mix64(seed ^ pn.rotate_left(17) ^ 0x4c41_4e5f_584f_525f);
            for chunk in bytes.chunks_mut(8) {
                state ^= state >> 12;
                state ^= state << 25;
                state ^= state >> 27;
                let ks = state.wrapping_mul(0x2545_f491_4f6c_dd1d).to_le_bytes();
                for (b, k) in chunk.iter_mut().zip(ks) { *b ^= k; }
            }
        }
    }
}

/// Each IPv4 packet becomes exactly one new TLS-looking application_data record.
/// The caller must avoid PN wrap. There is intentionally no authenticity.
fn seal(packet: &[u8], mode: Mode, seed: u64, pn: u64) -> Result<Vec<u8>, &'static str> {
    if !ipv4_packet_ok(packet) { return Err("not a single bounded IPv4 packet"); }
    let body = packet.len().checked_add(10).ok_or("length overflow")?;
    if body > MAX_TLS_BODY { return Err("TLS-like record budget exceeded"); }
    let mut wire = vec![0u8; OVERHEAD + packet.len()];
    wire[..3].copy_from_slice(&[0x17, 0x03, 0x03]);
    wire[3..5].copy_from_slice(&(body as u16).to_be_bytes());
    wire[5..13].copy_from_slice(&pn.to_be_bytes());
    wire[13..15].copy_from_slice(&(packet.len() as u16).to_be_bytes());
    wire[15..].copy_from_slice(packet);
    mask(&mut wire[13..], mode, seed, pn);
    Ok(wire)
}

fn open(wire: &[u8], mode: Mode, seed: u64) -> Result<(u64, Vec<u8>), &'static str> {
    if wire.len() < OVERHEAD + 20 || wire.len() > MAX_TLS_BODY + 5
        || wire[..3] != [0x17, 0x03, 0x03] { return Err("invalid outer header"); }
    let body = usize::from(u16::from_be_bytes([wire[3], wire[4]]));
    if body + 5 != wire.len() || body > MAX_TLS_BODY { return Err("outer length mismatch"); }
    let pn = u64::from_be_bytes(wire[5..13].try_into().map_err(|_| "missing PN")?);
    let mut plain = wire[13..].to_vec();
    mask(&mut plain, mode, seed, pn);
    let n = usize::from(u16::from_be_bytes([plain[0], plain[1]]));
    if n != plain.len() - 2 || !ipv4_packet_ok(&plain[2..]) {
        return Err("invalid inner packet");
    }
    // This check is only structural: malleable data can still be accepted.
    Ok((pn, plain[2..].to_vec()))
}

fn sample_ip_packet() -> Vec<u8> {
    let n = 1345;
    let mut p = vec![0u8; n];
    p[0] = 0x45;
    p[2..4].copy_from_slice(&(n as u16).to_be_bytes());
    p[6] = 0x40;
    p[8] = 64;
    p[9] = 6; // IPv4 / TCP
    p[12..20].copy_from_slice(&[10, 11, 12, 13, 10, 21, 22, 23]);
    p[20..24].copy_from_slice(&[0x12, 0x34, 0x01, 0xbb]);
    p[24..28].copy_from_slice(&140851678u32.to_be_bytes());
    p[32] = 0x50;
    for (i, b) in p[40..].iter_mut().enumerate() {
        *b = ((i * 37 + 11) & 255) as u8;
    }
    p
}

fn probe(port: u16) -> std::io::Result<()> {
    // Loopback TCP is genuinely established, but this is NOT the real Go/TLS
    // authentication or WBD TUN product path. The packets are bounded fixtures.
    let listener = TcpListener::bind(("127.0.0.1", port))?;
    let actual_port = listener.local_addr()?.port();
    let expected = sample_ip_packet();
    let receiver_expected = expected.clone();
    let server = thread::spawn(move || -> std::io::Result<()> {
        let (mut socket, _) = listener.accept()?;
        socket.set_read_timeout(Some(Duration::from_secs(10)))?;
        for (i, mode) in [Mode::FixedXor, Mode::FixedXor, Mode::RollingXor, Mode::RollingXor].iter().enumerate() {
            let mut head = [0u8; 5];
            socket.read_exact(&mut head)?;
            if head[..3] != [0x17, 0x03, 0x03] {
                return Err(std::io::Error::other("missing TLS-like application_data header"));
            }
            let body = usize::from(u16::from_be_bytes([head[3], head[4]]));
            if body > MAX_TLS_BODY || body < 30 {
                return Err(std::io::Error::other("invalid bounded record length"));
            }
            let mut wire = Vec::from(head);
            wire.resize(5 + body, 0);
            socket.read_exact(&mut wire[5..])?;
            let (pn, packet) = open(&wire, *mode, DEMO_SEED).map_err(std::io::Error::other)?;
            if pn != i as u64 || packet != receiver_expected {
                return Err(std::io::Error::other("decoded inner IPv4 packet mismatch"));
            }
        }
        Ok(())
    });
    let mut socket = TcpStream::connect(("127.0.0.1", actual_port))?;
    socket.set_nodelay(true)?;
    for (i, mode) in [Mode::FixedXor, Mode::FixedXor, Mode::RollingXor, Mode::RollingXor].iter().enumerate() {
        let wire = seal(&expected, *mode, DEMO_SEED, i as u64)
            .map_err(std::io::Error::other)?;
        socket.write_all(&wire)?;
        thread::sleep(Duration::from_millis(45));
    }
    drop(socket);
    server.join().map_err(|_| std::io::Error::other("receiver thread panic"))??;
    println!("{{\"scope\":\"ESTABLISHED_LOOPBACK_TCP_FIXTURE_NOT_WBD_TUN_OR_TLS_HANDSHAKE\",\"inner_ipv4_bytes\":1345,\"records\":4,\"fixed_xor\":2,\"rolling_xor\":2,\"inner_roundtrip\":true,\"auth\":\"NONE_INSECURE_OBFUSCATION\"}}");
    Ok(())
}

fn main() {
    let port: u16 = std::env::args().nth(1).expect("usage: lan_xor_tlslike_lab PORT")
        .parse().expect("port must be u16");
    probe(port).expect("loopback probe failed");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn packet_roundtrip_and_tlslike_length_exact() {
        let p = sample_ip_packet();
        for mode in [Mode::FixedXor, Mode::RollingXor] {
            for pn in [0, 1, 300, u64::MAX] {
                let w = seal(&p, mode, DEMO_SEED, pn).unwrap();
                assert_eq!(&w[..3], &[0x17, 0x03, 0x03]);
                assert_eq!(w.len(), 15 + p.len());
                assert_eq!(u16::from_be_bytes([w[3], w[4]]) as usize, w.len() - 5);
                assert_eq!(open(&w, mode, DEMO_SEED), Ok((pn, p.clone())));
            }
        }
    }

    #[test]
    fn full_packet_duplicate_fixed_repeats_rolling_does_not() {
        let p = sample_ip_packet();
        let f0 = seal(&p, Mode::FixedXor, DEMO_SEED, 0).unwrap();
        let f1 = seal(&p, Mode::FixedXor, DEMO_SEED, 1).unwrap();
        let r2 = seal(&p, Mode::RollingXor, DEMO_SEED, 2).unwrap();
        let r3 = seal(&p, Mode::RollingXor, DEMO_SEED, 3).unwrap();
        assert_eq!(&f0[15..143], &f1[15..143]); // 128B leak
        assert_ne!(&r2[15..79], &r3[15..79]);
        assert_ne!(&r2[15..143], &r3[15..143]);
        assert_ne!(&r2[15..], &p);
    }

    #[test]
    fn reject_bad_framing_and_lengths() {
        let p = sample_ip_packet();
        let mut w = seal(&p, Mode::RollingXor, DEMO_SEED, 9).unwrap();
        w[0] = 0x16;
        assert!(open(&w, Mode::RollingXor, DEMO_SEED).is_err());
        w[0] = 0x17; w[4] ^= 1;
        assert!(open(&w, Mode::RollingXor, DEMO_SEED).is_err());
        assert!(seal(&p[..10], Mode::RollingXor, DEMO_SEED, 1).is_err());
    }

    #[test]
    fn tampering_is_not_authenticated() {
        let p = sample_ip_packet();
        let mut w = seal(&p, Mode::RollingXor, DEMO_SEED, 4).unwrap();
        w[80] ^= 0x10; // not in IP header or length
        let (_, modified) = open(&w, Mode::RollingXor, DEMO_SEED).unwrap();
        assert_ne!(modified, p); // do not pretend this is a safe AEAD
    }

    #[test]
    fn replay_is_not_prevented() {
        let p = sample_ip_packet();
        let w = seal(&p, Mode::RollingXor, DEMO_SEED, 5).unwrap();
        assert_eq!(open(&w, Mode::RollingXor, DEMO_SEED),
                   open(&w, Mode::RollingXor, DEMO_SEED));
    }
}

#!/usr/bin/env bash
# Pure Java session-decision test, NOT an Android Framework runtime gate.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
# A34a: parse exact original Linux Oracle shell before expensive native builds.
bash -n android/root-native/ci/linux-original-oracle.sh
bash -n android/root-app/ci/x86-original-linux-server-prep.sh
mkdir -p out/android-root-app/network-scope-test
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/NetworkScopeGate.java \
  android/root-app/ci/NetworkScopeGateTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.NetworkScopeGateTest
# B27: execute exact production physical-underlay policy in plain JVM.
# INTERNET capability is deliberately not an input to this function;
# actual native socket+LinkProperties checks remain in PhysicalNetwork.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/PhysicalUnderlayPolicy.java \
  android/root-app/ci/PhysicalUnderlayPolicyTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.PhysicalUnderlayPolicyTest
# B28: exact production LAN peer-address selection helper, no DNS in Host.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/PhysicalPeerIPv4Choice.java \
  android/root-app/ci/PhysicalPeerIPv4ChoiceTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.PhysicalPeerIPv4ChoiceTest
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootStopCommand.java \
  android/root-app/ci/RootStopCommandTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootStopCommandTest
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootDirectIPv4.java \
  android/root-app/src/org/wbdnext/rootclient/RootPhysicalDNSUpstream.java \
  android/root-app/src/org/wbdnext/rootclient/OriginalGoCommandArgs.java \
  android/root-app/src/org/wbdnext/rootclient/RootRecoveryCommand.java \
  android/root-app/ci/RootRecoveryCommandTest.java \
  android/root-app/src/org/wbdnext/rootclient/AllAppUIDPolicy.java \
  android/root-app/src/org/wbdnext/rootclient/ServerAddress.java
# B33 original app cold direct-prefix normalizer, with no Android
# guest or per-packet FFI.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootDirectIPv4.java \
  android/root-app/ci/RootDirectIPv4Test.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootDirectIPv4Test
# B34 real original App physical upstream parser, no Android runtime mock.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootPhysicalDNSUpstream.java \
  android/root-app/ci/RootPhysicalDNSUpstreamTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootPhysicalDNSUpstreamTest
# B41 original Android Game2 real Go→Rust product path: TWO authenticated
# original TLS associations, same /32, exact Android Network, original
# grouped Rust M4; only AFTER M4 do ordinary UID routes apply.
python3 - <<'PY'
from pathlib import Path
g=Path("r0/go_overlay/internal/v4productcli/game_android.go").read_text()
bridge=Path("r0/go_overlay/internal/realityfront/bridge_v4_game_native_android.go").read_text()
go=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
guard=Path("r0/go_overlay/internal/v4productcli/rstguard/guard.go").read_text()
guardtest=Path("r0/go_overlay/internal/v4productcli/rstguard/guard_test.go").read_text()
build=Path("android/root-native/build-source-locked.sh").read_text()
app=Path("android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
assert 'return runAndroidGame(ctx,cfg,uint32(iface.Index),tun,&connected)' in go
assert 'func runAndroidGame(' in g
assert 'runAndroidGame(_ context.Context' in Path(
    "r0/go_overlay/internal/v4productcli/game_android_stub_linux.go").read_text()
assert 'rstguard.New(runFirewall' in g
assert 'Game2:c.gameLanes==2,Game4:c.gameLanes==4' in g
assert 'sourcePorts += ":"+strconv.Itoa(p.SourcePort+1)' in guard
assert 'sourcePorts += ":"+strconv.Itoa(p.SourcePort+3)' in guard
assert 'TestGame4OriginalFourPortOneOwnedRSTRule' in guardtest
assert 'TestGame2OriginalTwoPortOneOwnedRSTRule' in guardtest
assert 'raw.BindAndroidNetwork(c.androidNetworkHandle' in g
assert 'realityfront.NewV4AndroidGameProduct(' in g
assert 'native.ConnectAuthenticatedGame(tlsCtx,assocs,admission)' in g
assert 'raw.QuiesceDetachedClientReceive()' in g
assert g.index('raw.QuiesceDetachedClientReceive()')<g.index('androidRootRouteAfterNative(c,tun,lease)')
assert 'V4LinuxGameClientVerifiedGroup(p.sessions...)' in bridge
assert 'EstablishClientV4(ctx,assoc.BootstrapConn(),laneCfg' in bridge
assert 'owner.prepareAuthenticatedClient(session,handoff,assoc.Flow())' in bridge
assert 'owner.bindAuthenticatedClientIPv4(current)' in bridge
assert 'v4BindPlatformUnderlay(owner,V4LinuxClientProductConfig{' in bridge
assert 'C.wbd_m0_embedded_go_game_group_join(' in bridge
assert 'C.wbd_m0_embedded_go_android_game_group_raw_bind(' in bridge
assert 'C.wbd_m0_embedded_go_android_game_group_m4_start(' in bridge
# B42 original App Game2/off UI→Service→Go argv, not a new data plane.
service=Path("android/root-app/src/org/wbdnext/rootclient/RootClientService.java").read_text()
argv=Path("android/root-app/src/org/wbdnext/rootclient/OriginalGoCommandArgs.java").read_text()
settings=Path("android/root-app/src/org/wbdnext/rootclient/RootConnectionSettings.java").read_text()
assert '"game2".equals(fecModes.getSelectedItem().toString())' in app
assert 'request.putExtra("fec_mode",fecMode);' in app
assert '!"fec-auto".equals(fecMode)&&!"game2".equals(fecMode)&&' in service
assert '!"game4".equals(fecMode)' in service
assert 'if("game2".equals(fecMode)&&(physicalDNS||cnSplitDNS))' not in service
assert 'pair(args,"--mode",productMode);' in argv
assert 'if("game2".equals(fecMode)&&(physicalDNS||cnSplitDNS))' not in argv
assert '!oneOf(mode,"normal","fec-fixed","fec-auto","game2","game4",' in settings
assert '"game2-fixed","game4-fixed")' in settings
assert bridge.index('C.wbd_m0_embedded_go_game_group_stop(') < bridge.index(
    'owner.StopAndReleaseOriginalOwner()')
assert 'new String[]{"normal","fec-fixed","fec-auto","game2","game4","game2-fixed","game4-fixed"}' in app
assert 'go_tags=wbd_v4_embedded_go' in build
# B47: signed App Service consumes *actual* Game2/4 Go native
# READY and does not overwrite a live Root owner's cold credential files.
service=Path("android/root-app/src/org/wbdnext/rootclient/RootClientService.java").read_text()
game_status=Path("android/root-app/src/org/wbdnext/rootclient/RootGameSessionStatus.java").read_text()
assert 'RootGameSessionStatus.gameReady(fecMode,line)' in service
assert 'RootGameSessionStatus.readyBrief(fecMode)' in service
assert 'RootGameSessionStatus.confirmedPreviousOwnerStop(' in service
assert 'nativeStopSeen,routeStopSeen,exit==0,uidReady' in service
assert 'sessionOwnerActive=true;' in service
assert 'sessionOwnerActive=false;' in service
assert 'RootGameSessionStatus.session' not in game_status
assert 'V4_ORIGINAL_ANDROID_GAME_NATIVE_READY role=client lanes=' in game_status
assert 'if(RootClientService.sessionOwnerActive||' in app
assert '切换实体Network：STOP旧会话' in app
print("ANDROID_B47_GAME_NATIVE_APP_LIFECYCLE_COLD_NETWORK_RESELECT_SOURCE_PASS")
# B48 actual group Stop: withdraw original UID policy before Rust
# joined Stop, join the old cold RTO/RAW Go owners and clear the exact
# durable RST guard. Only an error-free READY product can emit final
# Stop, and the App requires a Game-specific completed group marker.
assert g.index('routeErr=undoRoute()') < g.index('closeErr:=native.Close()')
assert 'V4_PUBLIC_ANDROID_UID_ROUTE_STOP_DRAINED role=client' in g
assert 'retErr=errors.Join(retErr,routeErr,closeErr)' in g
assert 'retErr=errors.Join(retErr,stopErr)' in g
assert 'retErr=errors.Join(retErr,r.Close())' in g
assert 'if guard!=nil{' in g
assert 'retErr=errors.Join(retErr,fmt.Errorf("Game2/4 RST guard owned Stop failed: %w",err))' in g
assert 'if productReady&&retErr==nil{' in g
assert 'V4_PUBLIC_ANDROID_GAME_STOP_JOINED role=client lanes=%d' in g
assert 'V4_PUBLIC_NATIVE_STOP_DRAINED role=client' in g
assert 'RootGameSessionStatus.gameGroupStopped(fecMode,line)' in service
assert 'fecMode,gameStopSeen,nativeStopSeen,routeStopSeen,exit==0,uidReady' in service
assert 'static final AtomicBoolean startDispatchPending=' in service
assert 'startDispatchPending.compareAndSet(false,true)' in app
assert 'startDispatchPending.set(false)' in service
assert 'ORIGINAL_GO_GAME_GROUP_STOP_JOINED' in Path(
    "android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java").read_text()
assert 'static boolean gameGroupStopped(' in game_status
assert 'expectedLanes(selectedMode)==0||groupStopped' in game_status
print("ANDROID_B48_ORIGINAL_GAME2_GAME4_ACTUAL_GO_RUST_UID_RST_STOP_SOURCE_PASS")
# B49 uses the existing 1Hz Activity refresh, true owned Stop, exact Network,
# and the actual original Activity start() (not a Java fake Root).
cold=Path("android/root-app/src/org/wbdnext/rootclient/RootColdNetworkSwitch.java").read_text()
assert 'completeUserColdSwitchIfReady();' in app
assert 'RootClientService.previousOwnerStopConfirmed' in app
assert 'coldSwitch.complete(' in app and 'coldSwitch.arm(target.handle' in app
assert 'PhysicalNetwork.exact(this,n.handle' in app
assert 'networks.setSelection(matched);' in app
assert 'ui.postDelayed(this,1000);' in app
assert 'coldSwitch.cancel();' in app
assert 'oldStopVerified&&targetStillPresent' in cold
print("ANDROID_B49_FOREGROUND_COLD_NETWORK_SOURCE_PASS")
# B50 named connection profiles are COLD UI only, never another
# native/TUN/RAW reader or credentials/physical Network serializer.
profile=Path("android/root-app/src/org/wbdnext/rootclient/RootConnectionProfile.java").read_text()
profile_store=Path("android/root-app/src/org/wbdnext/rootclient/RootConnectionProfileStore.java").read_text()
assert 'RootConnectionProfileStore.save(this,slot,profile)' in app
assert 'RootConnectionProfileStore.load(this,slot)' in app
assert 'RootConnectionProfileStore.delete(this,slot)' in app
assert 'restoreConnectionSettings(profile.settings)' in app
assert 'chooseInstalledApplications(); // current Android package/UID only' in app
assert 'restoredSelection.clear();' in app and 'restoredBypass.clear();' in app
assert 'for(CheckBox box:checkedApps.values())box.setChecked(false)' in app
assert 'RootConnectionSettings.read(' in profile
assert 'settings.write(settingsBytes)' in profile
assert 'getNoBackupFilesDir()' in profile_store
assert 'start();' in app
print("ANDROID_B50_NAMED_ROOT_UI_PROFILES_PRODUCTION_SOURCE_PASS")
# B51 real per-profile remembered credentials: reuse A38 AES-GCM store,
# no second encryption format, Account/TLS ABI or original native flags.
encrypted=Path("android/root-app/src/org/wbdnext/rootclient/RootEncryptedCredentialStore.java").read_text()
for token in ('saveProfile(Context ctx,int slot','loadProfile(Context ctx,int slot',
              'clearProfile(Context ctx,int slot','saveFile(profileFile(ctx,slot)',
              'return loadFile(profileFile(ctx,slot))',
              'RootSavedCredentialRecord.encrypt(key(true),password,shortKey)',
              'RootSavedCredentialRecord.decrypt(key(false),ciphertext)'):
 assert token in encrypted
assert 'RootEncryptedCredentialStore.saveProfile(this,slot,' in app
assert 'RootEncryptedCredentialStore.activateProfile(this,slot)' in app
assert 'RootSavedCredentialRecord.Secrets activateProfile(' in encrypted
assert 'else saveFile(file(ctx),selected.password,selected.routeKey);' in encrypted
assert 'if(selected==null)deleteFile(file(ctx));' in encrypted
assert 'RootEncryptedCredentialStore.clearProfile(this,slot)' in app
assert 'password.setText(saved==null?"":saved.password)' in app
assert 'routeKey.setText(saved==null?"":saved.routeKey)' in app
print("ANDROID_B51_PROFILE_SCOPED_EXISTING_KEYSTORE_SOURCE_PASS")
# B52: real signed Root Activity chooses saved profile and current Network,
# routes through the existing old owner Stop and original START, no new daemon.
cold=Path("android/root-app/src/org/wbdnext/rootclient/RootColdNetworkSwitch.java").read_text()
assert 'void armProfile(int slot,' in cold
assert 'int profileSlot()' in cold
assert 'profileSlot=0;' in cold
assert 'int slot=coldSwitch.profileSlot();' in app
assert 'RootClientService.previousOwnerStopConfirmed,matched>=0' in app
assert 'if(slot!=0&&!loadNamedProfile(slot))' in app
assert 'coldSwitch.armProfile(slot,target.handle' in app
assert 'RootConnectionProfileStore.load(this,slot)' in app
assert 'RootEncryptedCredentialStore.loadProfile(this,slot)' in app
assert 'connectProfile.setOnClickListener(v->connectSelectedSavedProfile())' in app
assert 'RootClientService.STOP' in app
assert 'if(loadNamedProfile(slot))start();' in app
assert 'refreshNamedProfileChoices();' in app
assert 'connect.setOnClickListener(v->{coldSwitch.cancel();start();})' in app
print("ANDROID_B52_NAMED_PROFILE_ORIGINAL_GO_RUST_SINGLE_ACTION_SWITCH_SOURCE_PASS")
# B53: original B50 4-slot nonsecret profile codec + SAF import/export.
bundle=Path("android/root-app/src/org/wbdnext/rootclient/RootConnectionProfileBundle.java").read_text()
assert 'RootConnectionProfileBundle.write(out,snapshot)' in app
assert 'RootConnectionProfileBundle.read(in)' in app
assert 'RootConnectionProfileStore.load(this,i+1)' in app
assert 'RootConnectionProfileStore.save(this,slot,restored[i])' in app
assert 'RootConnectionProfileStore.delete(this,slot)' in app
assert 'RootEncryptedCredentialStore.clearProfile(this,slot)' in app
assert ('RootEncryptedCredentialStore.clearProfile(this,slot);' +
        chr(10) + '                RootConnectionProfileCAStore.clearSlot(this,slot);') in app
assert 'coldSwitch.cancel();' in app
assert 'PROFILE_BUNDLE_EXPORT=2046' in app and 'PROFILE_BUNDLE_IMPORT=2047' in app
assert 'profile.write(payload)' in bundle
assert 'RootConnectionProfile.read(' in bundle
print("ANDROID_B53_FOUR_SAF_PROFILE_IMPORT_EXPORT_ORIGINAL_SETTINGS_SOURCE_PASS")
# B54: optional user CA follows the selected Root profile, not
# the previous server's single global UI field. Original strict TLS/off
# choice and original Go private CA handoff remain unchanged.
profile_ca=Path("android/root-app/src/org/wbdnext/rootclient/RootConnectionProfileCAStore.java").read_text()
assert 'RootConnectionProfileCAStore.saveSlot(this,slot,' in app
assert 'RootConnectionProfileCAStore.loadSlot(this,slot)' in app
assert 'RootConnectionProfileCAStore.saveCurrent(this,storedCA)' in app
assert 'caPEM.setText(storedCA);' in app
assert 'RootConnectionProfileCAStore.loadCurrent(this)' in app
assert 'RootConnectionProfileCAStore.clearSlot(this,slot)' in app
assert 'RootConnectionProfileCAStore.saveCurrent(this,pem)' in app
assert 'RootPrivateCredentialContract.maxBytes(RootPrivateCredentialFiles.CA)' in profile_ca
assert 'getNoBackupFilesDir()' in profile_ca
assert 'RootPrivateCredentialFiles.CA,pem+' in app
assert 'tls_verify_server' in app
print("ANDROID_B54_OPTIONAL_PER_PROFILE_ORIGINAL_GO_TLS_CA_COLD_SOURCE_PASS")





# B43: Game2 shares original Normal UDP53, native Health and M4 counters.
rust_group=Path("crates/wbd-engine/src/v4_embedded_go.rs").read_text()
m4=Path("crates/wbd-engine/src/v4_android_game_m4.rs").read_text()
fec_status=Path("android/root-app/src/org/wbdnext/rootclient/RootFecStateBrief.java").read_text()
assert 'TunnelDNS:c.androidTunnelDNS' in g
assert 'HealthSeconds:c.androidNativeHealthSeconds' in g
assert 'tunnel_dns:u32,health_seconds:u32' in rust_group
assert 'tunnel_dns==1,health_seconds' in rust_group
assert 'dns,C.uint32_t(p.cfg.HealthSeconds)' in bridge
assert 'TunnelDnsUdpFlows::default()' in m4
assert 'table.rewrite_query(&mut source[..n]' in m4
assert 'table.rewrite_reply(' in m4
assert m4.index('opener.open(&mut wire[..len])')<m4.index('table.rewrite_reply(')
assert 'HealthPolicy::new(u64::from(health_seconds)*1_000_000_000' in m4
assert 'OriginalM4Counters()' in g
assert 'V4_PUBLIC_ANDROID_GAME2_M4_COUNTERS role=client' in g
assert 'gameCounters(String line)' in fec_status
# B44 original selected Network physical UDP53 and pinned CN8503 cold
# classifier share this same Game2 single-TUN M4; no extra Go DATA path.
platform=Path("crates/wbd-platform/src/android_root_io.rs").read_text()
dns_router=Path("crates/wbd-engine/src/v4_android_dns_route.rs").read_text()
assert 'PhysicalDNS:c.androidPhysicalDNS' in g
assert 'PhysicalDNSUpstream:c.androidPhysicalDNSUpstream' in g
assert 'CN8503Raw:cn8503Raw' in g
assert 'c.androidCNSnapshot.PinnedWire()' in g
assert 'PhysicalDNSUpstream netip.Addr' in bridge
assert 'CN8503Raw []byte' in bridge
assert 'C.size_t(len(p.cfg.CN8503Raw))' in bridge
assert 'physical_dns:u32,upstream:*const u8' in rust_group
assert 'CNDnsMatcher::from_go_cold(cold)' in rust_group
assert 'physical_dns==1,physical_upstream,cn' in rust_group
assert 'AndroidBoundPhysicalDnsUdp::open(' in m4
assert 'PhysicalDnsUdpFlows::default()' in m4
assert 'let route=choose(&source[..n]' in m4
assert 'physical_flows.prepare(&source[..n]' in m4
assert 'physical_flows.receive(' in m4
assert 'tx_tun.write_scoped_physical_dns_ip(' in m4
assert 'tx_wake.wait_tun_and_physical_dns(' in m4
assert 'socket.stop_until(' in m4
assert 'DnsRoute::TCP53OriginalTunnel' in dns_router
assert 'pub struct AndroidBoundPhysicalDnsUdp' in platform
assert 'original Android TUN/physical DNS poll invalid' in platform
assert 'gameCounters(String line)' in fec_status
assert '"physicaltx=","physicalrx=","physicalerr="' in fec_status
# B45: four genuine Go TLS/FakeTCP lanes, one GameAdapter,
# 4 exact RAW RX, one TUN TX and the same native Game4 copy scheduler.
assert '(cfg.gameLanes==2||cfg.gameLanes==4)' in go
assert 'c.gameLanes!=2&&c.gameLanes!=4' in g
assert 'DesiredLanes:c.gameLanes' in g
assert 'len(assocs)!=int(p.cfg.Lanes)' in bridge
assert 'len(cold)!=int(p.cfg.Lanes)' in bridge
assert 'ids:=make([]C.uint64_t,len(cold))' in bridge
assert 'bound!=C.uint32_t(p.cfg.Lanes)' in bridge
assert 'lanes!=uint32(p.cfg.Lanes)' in bridge
assert 'g.android_lanes.len(),2|4' in rust_group
assert 'let lane_count=lanes.len();' in m4
assert 'for i in 0..lane_count' in m4
assert 'for id in 1..=lane_count' in m4
assert 'let mut outer=[[0u8;2048];4];' in m4
assert 'game.configure_game4_stagger_mode(2)' in m4
assert 'game.game4_next_due_ns()' in m4
assert 'drain_original_game!(game,when)' in m4
assert 'Game4 bool' in guard
assert 'TestGame4OriginalFourPortOneOwnedRSTRule' in guardtest
assert 'V4_PUBLIC_ANDROID_GAME4_M4_COUNTERS role=client' in g
assert 'V4_PUBLIC_ANDROID_GAME4_M4_COUNTERS role=client' in fec_status
assert '"game4".equals(fecModes.getSelectedItem().toString())' in app
# B46: restore the REAL B45 Game4 M4 gate (previously hardcoded
# raw v.len()==2), plus reuse original Linux Game fixed FEC for Android.
assert '.filter(|v|v.len()==g.android_lanes.len())' in rust_group
assert '(game_fec_profile!=255).then_some(game_fec_profile as u8)' in rust_group
assert 'GameFecEnabled:c.gameFecEnabled' in g
assert 'GameFecProfile:c.gameFecProfile' in g
assert 'extension.GameFec!=opt.GameFec' in Path(
    "r0/go_overlay/internal/realityfront/admission_v4.go").read_text()
assert 'GameFec:negotiatedFec,StartupPadding:0' in bridge
assert 'GameFec:negotiatedFec,StartupPadding:0' in bridge
assert 'OriginalGameFecCounters()' in g
assert 'C.wbd_fec_network_game_group_counters(' in bridge
assert 'game.enable_game_fec(profile,false)' in m4
assert 'game.poll_game_fec(fec_now)' in m4
assert 'game.game_fec_next_due_ns(when)' in m4
assert 'owner.prepare_opened_fec_batch(' in m4
assert 'owner.finish_fec_batch(' in m4
assert 'for frame in batch.frames_mut()' in m4
assert 'rx_tun.write_authenticated_ip(frame)' in m4
assert 'pub(crate) fn frames_mut(' in Path(
    "crates/wbd-engine/src/v4_game_lane.rs").read_text()
assert 'game2-fixed' in app and 'game4-fixed' in app
assert 'pair(args,"--game-fec","fixed"+fecProfile)' in argv
assert 'V4_PUBLIC_ANDROID_GAME_FEC_COUNTERS role=client' in g
assert 'gameFixedCounters(String line)' in fec_status
print("ANDROID_B46_ORIGINAL_GAME_FIXED_FEC_2_4_TLS_RUST_M4_APP_PRODUCTION_SOURCE_PASS")
print("ANDROID_B45_GAME4_OFF_FOUR_ORIGINAL_TLS_ONE_RUST_M4_STAGGER_APP_SOURCE_PASS")
print("ANDROID_B44_GAME2_ORIGINAL_PHYSICAL_CN8503_SINGLE_TUN_DNS_SOURCE_PASS")
print("ANDROID_B43_GAME2_ORIGINAL_M4_TUNNEL_DNS_HEALTH_COUNTERS_SOURCE_PASS")
print("ANDROID_B41_REAL_GO_TLS_GAME2_OFF_SAME_RUST_M4_ROOT_UID_AND_OWNED_STOP_SOURCE_PASS")
PY
# B40: real Rust Game2/off TX TUN reader and two original M3 lane RX
# workers are compiled as part of the SAME GameAdapter.
python3 - <<'PY'
from pathlib import Path
g=Path("crates/wbd-engine/src/v4_embedded_go.rs").read_text()
m=Path("crates/wbd-engine/src/v4_android_game_m4.rs").read_text()
b=Path("android/root-native/build-source-locked.sh").read_text()
assert 'android_workers:Option<android_game_m4::AndroidGameWorkers>' in g
assert 'wbd_m0_embedded_go_android_game_group_m4_start(' in g
assert 'wbd_m0_embedded_go_android_game_group_m4_counters(' in g
assert 'AndroidGameWorkers::start(' in g
assert 'workers.stop_and_drain()' in g
assert 'drivers_installed.write(u32::from(e.android_workers.as_ref()' in g
assert 'AndroidOwnedTun::adopt(fd,tun_name,generation)' in m
assert 'rx.take_lane_for_worker(' in m
assert 'rx_raw.read_original_record(' in m
assert 'opener.open(&mut wire[..len])' in m
assert 'owner.prepare_opened_receive(' in m
assert 'owner.finish_receive(packet,written)' in m
assert 'game.offer(&source[..n],now)' in m
# B45 same original GameAdapter RAW sender is shared by TUN ingress
# and Game4 due ticks, instead of the B40 inlined one-time drain.
assert 'drain_original_game!(game,now)' in m
assert 'drain_original_game!(game,when)' in m
assert 'tx_raw[i].send_built_outer(' in m
assert 'HealthClock::new(' in m
assert 'wbd_m0_embedded_go_android_game_group_m4_start' in b
print("ANDROID_B40_ORIGINAL_GAME2_OFF_BIONIC_RAW_TUN_M3_M4_NATIVE_SOURCE_PASS")
# B55 true Android Game2/4 Rust original worker, not fake Activity state.
schedule=Path("crates/wbd-engine/src/v4_android_game_schedule.rs").read_text()
assert 'let mut tun_burst=GameTunBurst::default();' in m
assert 'tun_burst.inline_next(received_business)' in m
assert 'health.next_deadline(),game_due' in m
assert 'rx_raw.readiness_fd(),RAW_RX_IDLE_MAX_MS' in m
assert 'game.game4_next_due_ns()' in m
assert 'game.game_fec_next_due_ns(when)' in m
assert 'IDLE_WAKE_MAX_MS:i32=1_000' in schedule
assert 'const MAX_INLINE_TUN_BURST:u8=8;' in schedule
assert 'mod v4_android_game_schedule;' in Path(
    "crates/wbd-engine/src/lib.rs").read_text()
# B55b physical UDP53 queries also rejoin the bounded M4 event loop
# after up to eight TUN reads; no accidental duplicate M3 forwarding.
physical_path=m.split('if matches!(route,DnsRoute::PhysicalUDP){',1)[1].split(
    '// Same 64-slot original Normal TunnelDnsUdpFlows,',1)[0]
assert 'continue' not in physical_path
assert '}else{' in physical_path
assert 'Physical UDP only uses scoped socket, never GameAdapter/M3.' in m
assert 'if tun_burst.inline_next(received_business){continue}' in m
# B56 original Game RAW RX: no sidecar and no extra packet queues.
assert 'let mut raw_burst=GameTunBurst::default();' in m
assert 'let raw_received=matches!(&read,Ok((n,_)) if *n>0);' in m
assert 'if raw_burst.inline_next(raw_received){continue}' in m
assert 'rx_raw.readiness_fd(),RAW_RX_IDLE_MAX_MS' in m
assert 'pub(crate) const RAW_RX_IDLE_MAX_MS:i32=30_000' in schedule
workflow=Path(".github/workflows/android-root-product-a1.yml").read_text()
assert '      - "crates/wbd-engine/src/v4_android_game_*.rs"' in workflow
print("ANDROID_B56_ORIGINAL_GAME_2_4_M3_RX_BURST_EVENT_STOP_SOURCE_PASS")
# B57: actual original Game2/4 TUN full App IPv4 / physical UDP53
# or original RFC791 DF0→GameAdapter M3 and local DF1 ICMP PMTU.
ipv4=Path("crates/wbd-engine/src/v4_android_ipv4_mtu.rs").read_text()
assert 'n>0&&admitted_client_source(&source[..n],Some(lease))' in m
assert 'emit_game_ipv4_fragments(' in m
assert 'game.offer(piece,now)' in m
assert 'drain_original_game!(game,now)' in m
assert 'fragmentation_needed(' in m
assert 'tx_tun.write_local_pmtu_icmp_ipv4(' in m
assert 'let mut game_ipv4_fragment=[0u8;2_048]' in m
assert 'fn emit_game_ipv4_fragments<' in ipv4
assert 'can_fragment(original)' in ipv4
assert 'if matches!(route,DnsRoute::PhysicalUDP)' in m
print("ANDROID_B57_GAME_IPV4_DF0_DF1_PMTU_ORIGINAL_M3_SOURCE_PASS")
print("ANDROID_B55B_GAME_PHYSICAL_DNS_REPLY_FAIRNESS_SOURCE_PASS")
print("ANDROID_B55_ORIGINAL_GAME2_GAME4_LOW_WAKE_AND_TUN_BURST_SOURCE_PASS")
PY
# B39: original native Rust Game groups on Android now bind exactly one
# Bionic physical Network and independent RAW RX/TX per authenticated lane.
# This is cold-only; a Game M4/TUN worker and App mode are NOT READY.
python3 - <<'PY'
from pathlib import Path
engine=Path("crates/wbd-engine/src/v4_embedded_go.rs").read_text()
game=Path("crates/wbd-engine/src/v4_android_game_cold.rs").read_text()
platform=Path("crates/wbd-platform/src/android_root_io.rs").read_text()
build=Path("android/root-native/build-source-locked.sh").read_text()
assert 'canonical_original_game_lanes(' in engine
assert 'struct AndroidGameRawLane' in engine
assert 'android_physical:AndroidPhysicalScope' in engine
assert 'android_raw:Option<Vec<AndroidGameRawLane>>' in engine
assert 'if scope.as_ref().is_some_and(|old|old!=physical)' in engine
assert 'AndroidBoundRawRx::open_exact(' in engine
assert 'AndroidBoundRawTx::open(' in engine
assert 'wbd_m0_embedded_go_android_game_group_raw_bind(group:u64)' in engine
assert 'wbd_m0_embedded_go_android_game_group_raw_state(' in engine
assert 'lane.rx.stop_until(deadline)' in engine
assert 'lane.tx.stop_until(deadline)' in engine
assert 'drivers_installed.write(0)' in engine
assert 'exact_raw_tcp_filter(' in platform
assert 'wbd_m0_embedded_go_android_game_group_raw_bind' in build
assert 'android_game_cold_original_two_tls_lanes_use_slot_not_arrival' in game
print("ANDROID_B39_ORIGINAL_GAME2_COLD_TLS_GROUP_BOUND_RAW_AND_OWNED_STOP_SOURCE_PASS")
PY
# B38: actual selected LinkAddress IPv4 subnet uses existing Go private
# UID FIB throw route, not another Java kernel route engine or packet pump.
python3 - <<'PY'
from pathlib import Path
base=Path("android/root-app/src/org/wbdnext/rootclient")
network=(base/"PhysicalNetwork.java").read_text()
ui=(base/"RootClientActivity.java").read_text()
svc=(base/"RootClientService.java").read_text()
arg=(base/"OriginalGoCommandArgs.java").read_text()
go=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
assert 'chosen.matchesLinkProperties(link)' in network
assert 'RootDirectIPv4.connectedSubnet(chosen.address,' in network
assert 'RootDirectIPv4.withConnectedSubnet(directCIDRs,subnet)' in ui
assert 'request.putExtra("direct_lan_auto",autoConnectedDirect.isChecked())' in ui
assert 'RootDirectIPv4.includes(directCIDRs,localSubnet)' in svc
assert 'pair(args,"--android-direct-cidrs",direct)' in arg
assert 'rootjournal.ParseDirectCIDRs(*androidDirectCIDRs)' in go
print("ANDROID_B38_CONNECTED_REAL_NETWORK_IPV4_SUBNET_TO_ORIGINAL_GO_UID_FIB_SOURCE_PASS")
PY
# B37: one cold Go-to-native Health policy, not a Go heartbeat worker.
python3 - <<'PY'
from pathlib import Path
a=Path("android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
s=Path("android/root-app/src/org/wbdnext/rootclient/RootClientService.java").read_text()
argv=Path("android/root-app/src/org/wbdnext/rootclient/OriginalGoCommandArgs.java").read_text()
go=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
product=Path("r0/go_overlay/internal/realityfront/bridge_v4_linux_client_product.go").read_text()
assert 'request.putExtra("native_health_seconds",nativeHealthSeconds)' in a
assert 'intent.getIntExtra("native_health_seconds",15)' in s
assert 'pair(args,"--android-native-health-seconds",Integer.toString(nativeHealthSeconds))' in argv
assert 'androidNativeHealth:=flags.Uint("android-native-health-seconds",15,' in go
assert 'HealthKeepaliveSeconds:c.androidNativeHealthSeconds' in go
assert 'bridge.configureOriginalNativeHealth(keepalive,dead,p.cfg.HealthIdleDormantSeconds)' in product
print("ANDROID_B37_ACTUAL_RUST_M4_HEALTH_COLD_WIRING_SOURCE_PASS")
PY
# B36: the exact selected Android Network supplies DNS only at START.
python3 - <<'PY'
from pathlib import Path
p=Path("android/root-app/src/org/wbdnext/rootclient")
network=(p/"PhysicalNetwork.java").read_text()
activity=(p/"RootClientActivity.java").read_text()
service=(p/"RootClientService.java").read_text()
settings=(p/"RootConnectionSettings.java").read_text()
assert 'chosen.matchesLinkProperties(link)' in network
assert 'RootPhysicalDNSUpstream.firstSelectedIPv4(link.getDnsServers())' in network
assert 'PhysicalNetwork.selectedDNSIPv4(this,scope)' in activity
assert 'request.putExtra("physical_dns_follow_network",physicalDNSFollowNetwork.isChecked())' in activity
assert 'PhysicalNetwork.selectedDNSIPv4(this,chosen)' in service
assert 'p.setProperty("physical_dns_follow_network"' in settings
print("ANDROID_B36_REAL_SELECTED_NETWORK_DNS_COLD_GO_RUST_SOURCE_PASS")
PY
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootRecoveryCommandTest
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/InstalledAppTarget.java \
  android/root-app/ci/InstalledAppTargetTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.InstalledAppTargetTest
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/InstalledAppTarget.java \
  android/root-app/src/org/wbdnext/rootclient/SelectedAppGroup.java \
  android/root-app/ci/SelectedAppGroupTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.SelectedAppGroupTest
# B24: production local App search and bounded multi-UID batch selection.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/InstalledAppTarget.java \
  android/root-app/src/org/wbdnext/rootclient/SelectedAppGroup.java \
  android/root-app/src/org/wbdnext/rootclient/RootAppPickerModel.java \
  android/root-app/ci/RootAppPickerModelTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootAppPickerModelTest
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/AllAppUIDPolicy.java \
  android/root-app/ci/AllAppUIDPolicyTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.AllAppUIDPolicyTest
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/ServerAddress.java \
  android/root-app/ci/ServerAddressTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.ServerAddressTest
# B22: exact production non-secret connection UI settings codec;
# native TLS/Root, physical Network and UID route are never restored here.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/ServerAddress.java \
  android/root-app/src/org/wbdnext/rootclient/InstalledAppTarget.java \
  android/root-app/src/org/wbdnext/rootclient/SelectedAppGroup.java \
  android/root-app/src/org/wbdnext/rootclient/RootDirectIPv4.java \
  android/root-app/src/org/wbdnext/rootclient/AllAppUIDPolicy.java \
  android/root-app/src/org/wbdnext/rootclient/RootPhysicalDNSUpstream.java \
  android/root-app/src/org/wbdnext/rootclient/RootConnectionSettings.java \
  android/root-app/ci/RootConnectionSettingsTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootConnectionSettingsTest
# B26: same production SAF importer, accepts B25 16 package UID presets,
# bounded to 8KiB and never carries native secrets or physical handles.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/ServerAddress.java \
  android/root-app/src/org/wbdnext/rootclient/InstalledAppTarget.java \
  android/root-app/src/org/wbdnext/rootclient/SelectedAppGroup.java \
  android/root-app/src/org/wbdnext/rootclient/RootDirectIPv4.java \
  android/root-app/src/org/wbdnext/rootclient/AllAppUIDPolicy.java \
  android/root-app/src/org/wbdnext/rootclient/RootPhysicalDNSUpstream.java \
  android/root-app/src/org/wbdnext/rootclient/RootConnectionSettings.java \
  android/root-app/src/org/wbdnext/rootclient/RootConnectionSettingsTransfer.java \
  android/root-app/ci/RootConnectionSettingsTransferTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootConnectionSettingsTransferTest
# B50 host-run production named profile codec across Normal/Auto/Game.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/ServerAddress.java \
  android/root-app/src/org/wbdnext/rootclient/InstalledAppTarget.java \
  android/root-app/src/org/wbdnext/rootclient/SelectedAppGroup.java \
  android/root-app/src/org/wbdnext/rootclient/RootDirectIPv4.java \
  android/root-app/src/org/wbdnext/rootclient/AllAppUIDPolicy.java \
  android/root-app/src/org/wbdnext/rootclient/RootPhysicalDNSUpstream.java \
  android/root-app/src/org/wbdnext/rootclient/RootConnectionSettings.java \
  android/root-app/src/org/wbdnext/rootclient/RootConnectionSettingsTransfer.java \
  android/root-app/src/org/wbdnext/rootclient/RootConnectionProfile.java \
  android/root-app/ci/RootConnectionProfileTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootConnectionProfileTest
# B53: one actual SAF codec for all four named original Go/Rust profiles.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/ServerAddress.java \
  android/root-app/src/org/wbdnext/rootclient/InstalledAppTarget.java \
  android/root-app/src/org/wbdnext/rootclient/SelectedAppGroup.java \
  android/root-app/src/org/wbdnext/rootclient/RootDirectIPv4.java \
  android/root-app/src/org/wbdnext/rootclient/AllAppUIDPolicy.java \
  android/root-app/src/org/wbdnext/rootclient/RootPhysicalDNSUpstream.java \
  android/root-app/src/org/wbdnext/rootclient/RootConnectionSettings.java \
  android/root-app/src/org/wbdnext/rootclient/RootConnectionSettingsTransfer.java \
  android/root-app/src/org/wbdnext/rootclient/RootConnectionProfile.java \
  android/root-app/src/org/wbdnext/rootclient/RootConnectionProfileBundle.java \
  android/root-app/ci/RootConnectionProfileBundleTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootConnectionProfileBundleTest
# Execute the EXACT production RootService original Go argv builder on the
# host JVM. No Android guest, fake Network, Root permission or packet I/O.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/ServerAddress.java \
  android/root-app/src/org/wbdnext/rootclient/AllAppUIDPolicy.java \
  android/root-app/src/org/wbdnext/rootclient/RootDirectIPv4.java \
  android/root-app/src/org/wbdnext/rootclient/RootPhysicalDNSUpstream.java \
  android/root-app/src/org/wbdnext/rootclient/OriginalGoCommandArgs.java \
  android/root-app/ci/OriginalGoCommandArgsTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.OriginalGoCommandArgsTest
# A32 real Host POSIX filesystem metadata test of the EXACT production
# Android pre-su 0600 credential policy (no guest, NIC, Root or fake TLS).
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootPrivateCredentialContract.java \
  android/root-app/ci/RootPrivateCredentialContractTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootPrivateCredentialContractTest
# Actual Lite v2 Java KDF + immutable cache HMAC, matched to main Go
# short_test.go vectors. Pure local JVM, no Root, server, network or fake TLS.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootRouteKeyV2.java \
  android/root-app/ci/RootRouteKeyV2Test.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootRouteKeyV2Test
# A38 actual production AES-GCM record codec with standard JVM cipher;
# AndroidKeyStore adapter source is separately compiled by signed SDK36 APK.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootSavedCredentialRecord.java \
  android/root-app/ci/RootSavedCredentialRecordTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootSavedCredentialRecordTest
# The same production optional save wrapper used by the on-device START.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootStartCredentialSave.java \
  android/root-app/ci/RootStartCredentialSaveTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootStartCredentialSaveTest
# Exact production Root Service diagnostic writer, not a fabricated
# Android guest or Go/TLS success. Verify fixed enums, bounded retention,
# no untrusted metadata and Device acceptance report semantics.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java \
  android/root-app/ci/RootDiagnosticReceiptTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootDiagnosticReceiptTest
# Actual production report filtering and last-stage derivation; NEVER fake
# a Root device, fetch logcat, reveal source raw stdout or touch network.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java \
  android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReport.java \
  android/root-app/src/org/wbdnext/rootclient/RootDNSStatusBrief.java \
  android/root-app/ci/RootDiagnosticReportTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootDiagnosticReportTest
# B21: host-execute the production, on-demand Rust M4 real traffic brief.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java \
  android/root-app/src/org/wbdnext/rootclient/RootM4TrafficBrief.java \
  android/root-app/ci/RootM4TrafficBriefTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootM4TrafficBriefTest
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/OriginalGoMilestones.java \
  android/root-app/ci/OriginalGoMilestonesTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.OriginalGoMilestonesTest
# B49 production pure-JVM one-shot Network decision.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test android/root-app/src/org/wbdnext/rootclient/RootColdNetworkSwitch.java android/root-app/ci/RootColdNetworkSwitchTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootColdNetworkSwitchTest

# B47 signed-App original Game2/4 connection READY + owned Stop receipt.
# These are exact markers from real Go/Rust, never UI mode fake-ready.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/OriginalGoMilestones.java \
  android/root-app/src/org/wbdnext/rootclient/RootGameSessionStatus.java \
  android/root-app/ci/RootGameSessionStatusTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootGameSessionStatusTest

# B20: execute the SAME immutable native FEC status decoder embedded in
# the signed APK. No guest, test-only parser, network or forged APPLIED.
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/OriginalGoMilestones.java \
  android/root-app/src/org/wbdnext/rootclient/RootFecStateBrief.java \
  android/root-app/ci/RootFecStateBriefTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootFecStateBriefTest
PYTHONPATH=android/root-app/ci python3 -m unittest -v device_first_run_test
python3 android/root-app/ci/test-device-selftest-source.py
javac -source 8 -target 8 -encoding UTF-8 -d out/android-root-app/network-scope-test \
  android/root-app/src/org/wbdnext/rootclient/RootUidTunPacketScript.java \
  android/root-app/ci/RootUidTunPacketScriptTest.java
java -ea -cp out/android-root-app/network-scope-test org.wbdnext.rootclient.RootUidTunPacketScriptTest
python3 - <<'PY'
from pathlib import Path
s=Path("android/root-app/src/org/wbdnext/rootclient/RootClientService.java").read_text()
for method in ("registerNetworkCallback(", "unregisterNetworkCallback(",
 "onLost(", "onLinkPropertiesChanged(", "onCapabilitiesChanged(",
 "onBlockedStatusChanged("):
 assert method in s, method
assert "postDelayed(" not in s, "no 1-second steady Network watcher"
assert "getNetworkCapabilities(" not in s and "getLinkProperties(" not in s, "no synchronous ConnectivityManager lookup inside callback"
assert 'read oldpid oldstart oldgeneration <' in s, "owner.pid has 3 fields; never fold generation into oldstart"
# A30: user's real Android API36 EXIT_1 PRE_TUN receipt must be
# classifiable only by actual fixed markers from the ROOT shell and
# original Go Bionic entry. Never capture native raw stdout in reports.
go_src=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
# A32 fixed-string checks use the same original Go parser source. Keep
# this alias before all credential gates, not below their first use.
cold=go_src
receipt=Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java").read_text()
report=Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReport.java").read_text()
for marker in ["WBD_PUBLIC_ROOT_SHELL_ENTERED","WBD_PUBLIC_ROOT_UID_VERIFIED","WBD_PUBLIC_ROOT_PRIVATE_DIR_VERIFIED","WBD_PUBLIC_ROOT_OWNER_GUARD_PASSED","WBD_PUBLIC_ROOT_NATIVE_FILES_STAGED","WBD_PUBLIC_ROOT_OWNER_PID_WRITTEN","WBD_PUBLIC_ROOT_EXEC_ATTEMPTED"]:
 assert marker in s, "fixed Root shell stage missing: "+marker
for marker in ["V4_PUBLIC_ANDROID_GO_ENTRY role=client","V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client","V4_PUBLIC_ANDROID_GO_ARGS_ACCEPTED role=client","V4_PUBLIC_ANDROID_GO_INTERFACE_FOUND role=client","V4_PUBLIC_ANDROID_GO_TUN_OPEN_ATTEMPTED role=client","V4_PUBLIC_ANDROID_GO_TUN_OPENED role=client"]:
 assert marker in go_src and marker in s, "original Go stage not connected: "+marker
for event in ["START_DIAGNOSTIC_STAGES_V2","ROOT_PROCESS_EXIT_1","ROOT_SHELL_EXEC_ATTEMPTED","ORIGINAL_GO_ENTRY","ORIGINAL_GO_ARGS_REJECTED","ORIGINAL_GO_TUN_OPEN_ATTEMPTED"]:
 assert event in receipt, "diagnostic enum missing: "+event
assert 'if(has(session,"START_DIAGNOSTIC_STAGES_V2")' in report, "legacy receipts must not be misdiagnosed"
assert 'last_session_stage=' in report
assert 'OriginalGoMilestones.matches(line,' in s
assert 'RootFecStateBrief.fromGoLine(line)' in s
assert 'fecStatusText.setText(RootClientService.fecStatus)' in Path(
    "android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java"
).read_text()
assert 'V4_PUBLIC_ANDROID_FEC_STATE role=client mode=%s' in go_src
assert 'native.OriginalFECReadback()' in go_src
assert 'state!=lastFecState' in go_src
assert 'echo WBD_PUBLIC_ROOT_EXEC_ATTEMPTED' in s
assert 'log.Print("V4_PUBLIC_ANDROID_GO_ENTRY role=client")' in go_src

assert s.count('InstalledAppCatalog.stillSameGroup(this,targetPackages,targetUids)')>=2, "multi UID identity rechecked on Service and pre-su"
assert 'watchedAllAppPackages(managerPackages,bypassPackages)' in s and 'stopWatchingSelectedPackage()' in s, "withdraw selected group or manager exclusions on package events"
assert 'AllAppRouteScope.same(this,excludedAppIDs,managerPackages,' in s, "verify full-app owner+manager UID exclusions before su"
# B24: Ethernet exact Android Network selected and watched by one
# shared physical policy; refresh never silently changes valid selection.
physical=Path("android/root-app/src/org/wbdnext/rootclient/PhysicalNetwork.java").read_text()
assert 'NetworkCapabilities.TRANSPORT_ETHERNET' in physical
assert 'if(!physicalUnderlay(caps))' in physical
assert 'PhysicalNetwork.physicalUnderlay(caps)' in s
print("ANDROID_B24_ETHERNET_ORIGINAL_PHYSICAL_UNDERLAY_SOURCE_PASS")
# B27: a physically usable LAN does not require Android to call it
# an Internet-capable Network. Keep the same selected owner on a
# capability-only flip, with no auto-roam or new Rust/Go packet path.
assert 'PhysicalUnderlayPolicy.accepts(' in physical
assert 'caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN)' in physical
assert 'caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)' in physical
assert 'NetworkRequest request=new NetworkRequest.Builder()' in s
request=s.split('NetworkRequest request=new NetworkRequest.Builder()',1)[1].split('cm.registerNetworkCallback',1)[0]
assert '.addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)' not in request
assert '.addTransportType(NetworkCapabilities.TRANSPORT_ETHERNET)' in request
assert '.addTransportType(NetworkCapabilities.TRANSPORT_WIFI)' in request
assert '.addTransportType(NetworkCapabilities.TRANSPORT_CELLULAR)' in request
assert '[仅本地链路：Android未声明Internet]' in physical
assert '[公网未验证：可连接局域网WBD]' in physical
print("ANDROID_B27_LAN_ONLY_ANDROID_NETWORK_REQUEST_REAL_SERVICE_SOURCE_PASS")
assert 'NetworkCapabilities.NET_CAPABILITY_VALIDATED' in physical
assert 'PhysicalPeerIPv4Choice.select(network.getAllByName(peer))' in physical
assert 'network.getNetworkHandle()!=selected.handle' in physical
assert 'PhysicalNetwork.coldPeerIPv4(this,net,peer)' in s
assert 'launchCommand(code,net,peerForGo,sni' in s
assert 'ServerAddress.isIPv4Literal(peer)||selected.validatedByAndroid' in physical
assert 'LAN_SELECTED_NETWORK_CHANGED' in s
assert 'android.intent' not in physical
print("ANDROID_B28_EXACT_SELECTED_LAN_NETWORK_DNS_SERVER_BOOTSTRAP_SOURCE_PASS")
argv=Path("android/root-app/src/org/wbdnext/rootclient/OriginalGoCommandArgs.java").read_text()
assert 'OriginalGoCommandArgs.build(' in s, "production RootService must use host-tested original Go argv"
assert 'for(String a:args)quotedArgs.add(q(a))' in s, "every native argv token is shell quoted"
assert '"--android-route-all-apps"' in argv and '"--android-route-exclude-appids"' in argv, "original Go full-app CLI"
assert 'AllAppUIDPolicy.csv(excludedAppIDs)' in argv, "canonical app ID exclusions"
assert '"--android-route-uids"' in argv and '"--android-route-uid"' in argv, "original Go single and group UID flags"
assert 'ServerAddress.isIPv4Literal(peer)?"--peer-ip":"--peer-host"' in argv
assert 'ServerAddress.valid(peer)' in s
a=Path("android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
assert 'target_packages' in a and 'target_uids' in a
assert 'SelectedAppGroup.from(' in a and 'InstalledAppCatalog.stillSameGroup(' in a
assert 'RootConnectionSettingsStore.save(this,connectionSettingsFromUi())' in a
assert 'RootAppPickerModel.addMatching(' in a
assert 'RootAppPickerModel.matches(app,text)' in a
assert 'appSearch.addTextChangedListener(' in a
assert 'chooseNetworks();\n        chooseInstalledApplications();\n        refreshNamedProfileChoices();\n        ui.post(refreshStatus);' in a
assert 'physical.get(i).same(previouslySelected)' in a
print("ANDROID_B24_APP_PICKER_FILTER_BATCH_AND_NETWORK_REFRESH_SOURCE_PASS")
# B23: production Activity imports, recalls and clears ONE existing
# original Go 0600 private CA file, never changes Android system trust.
assert 'recallSavedTLSCA();' in a
assert 'privateText(RootPrivateCredentialFiles.CA,pem+' in a
assert 'file.delete()' in a
assert 'RootPrivateCredentialContract.maxBytes(' in a
assert 'java.security.cert.CertificateFactory.getInstance("X.509")' in a
print("ANDROID_B23_ORIGINAL_GO_LOCAL_CA_IMPORT_RECALL_CLEAR_SOURCE_PASS")
assert 'restoreConnectionSettings(RootConnectionSettingsStore.load(this))' in a
assert 'new TreeMap<>(restoredSelection)' in a
assert 'previous.get(app.packageName)==app.uid' in a
assert 'RootConnectionSettings' in Path(
 "android/root-app/src/org/wbdnext/rootclient/RootConnectionSettingsStore.java"
).read_text()
print("ANDROID_B22_PUBLIC_CONNECTION_SETTINGS_NO_BACKUP_REAL_APP_WIRING_PASS")
settings=Path("android/root-app/src/org/wbdnext/rootclient/RootConnectionSettings.java").read_text()
assert 'selected.size()>SelectedAppGroup.MAX_PACKAGES' in settings
assert 'uids.size()>SelectedAppGroup.MAX_UIDS' in settings
assert 'count>SelectedAppGroup.MAX_PACKAGES' in settings
print("ANDROID_B25_PRESET_NATIVE_UID_GROUP_RANGE_SOURCE_PASS")
assert 'RootConnectionSettingsTransfer.read(in)' in a
assert 'value.write(out)' in a
assert 'restoreConnectionSettings(imported)' in a
assert 'chooseInstalledApplications();' in a
assert 'RootConnectionSettingsStore.save(this,imported)' in a
assert 'CONNECTION_PRESET_EXPORT=2044' in a and 'CONNECTION_PRESET_IMPORT=2045' in a
print("ANDROID_B26_SAF_PRESET_REAL_ACTIVITY_EXPORT_IMPORT_SOURCE_PASS")
assert 'Integer.parseInt(uid.getText()' not in a, "no arbitrary hand-entered UID"
assert 'CheckBox' in a and 'appChoices' in a, "real visible multi-App selections"
assert 'allAppsDefault.setChecked(true)' in a, "all ordinary Android applications are the product UI default"
assert 'AllAppRouteScope.snapshot(this,bypassPackages,bypassUIDs)' in a and 'all_apps' in a, "default mode must pass verified scopes not fake overlay"

assert 'ServerAddress.valid(peer)' in a and 'Server underlay IPv4 or DNS name' in a
assert 'RootRouteKeyCache.resolve(this,sni,keyInput)' in a
# B8: Activity -> Service -> original Go -> existing Rust MTU budget.
assert 'outerMTUField.setText("1460")' in a
assert 'request.putExtra("outer_mtu",requestedOuterMTU)' in a
assert 'intent.getIntExtra("outer_mtu",1460)' in s
assert 'launchCommand(code,net,peerForGo,sni,user,port,requestedOuterMTU' in s
assert 'cnSplitDNS,requestedOuterMTU' in s
assert 'pair(args,"--outer-mtu",Integer.toString(requestedOuterMTU))' in argv
assert 'outerMTU:=flags.Int("outer-mtu",1460' in cold
assert 'deriveMTUBudget(c.outerMTU,' in cold
print("ANDROID_B8_ORIGINAL_GO_MTU_PRODUCTION_WIRING_SOURCE_PASS")
# B9: one original protected cipher choice, not a new Android AEAD.
assert 'recordCiphers.setAdapter(new ArrayAdapter' in a
assert 'request.putExtra("record_cipher",recordCipher)' in a
assert 'intent.getStringExtra("record_cipher")' in s
assert 'launchCommand(code,net,peerForGo,sni,user,port,requestedOuterMTU,recordCipher' in s
assert 'cnSplitDNS,requestedOuterMTU,recordCipher' in s
assert 'pair(args,"--record-cipher",recordCipher)' in argv
assert 'cipherName:=flags.String("record-cipher","chacha20-poly1305"' in cold
assert 'PolicyForClientWithInitialAndCipher(1,"off",0,4,20,c.recordCipher)' in cold
assert 'RecordSuite::try_from(identity.cipher)' in Path("crates/wbd-engine/src/v4_owner_crypto.rs").read_text()
print("ANDROID_B9_EXISTING_GO_M3_RUST_AUTHENTICATED_CIPHER_SOURCE_PASS")
# B10: same original Go cold path, bounded kernel TUN queue; no separate I/O.
assert 'tunQueueSizes.setAdapter(new ArrayAdapter' in a
assert 'request.putExtra("tun_txqlen",requestedTunQueue)' in a
assert 'intent.getIntExtra("tun_txqlen",500)' in s
assert 'launchCommand(code,net,peerForGo,sni,user,port,requestedOuterMTU,recordCipher,requestedTunQueue' in s
assert 'cnSplitDNS,requestedOuterMTU,recordCipher,requestedTunQueue' in s
assert 'pair(args,"--tun-txqlen-packets",Integer.toString(requestedTunQueue))' in argv
assert 'tunTxQLen:=flags.Int("tun-txqlen-packets",2048' in cold
assert 'setOwnedTunTxQueue(tun.name,cfg.tunTxQLenPackets)' in cold
assert 'validateOwnedTunTxQueueReadback' in cold
print("ANDROID_B10_ORIGINAL_GO_OS_TUN_QUEUE_PRODUCTION_WIRING_SOURCE_PASS")
# B11a: the original protected Normal mode reaches Bionic Rust M4, not Java DATA.
rust_m4=Path("crates/wbd-engine/src/v4_android_original_m4.rs").read_text()
rust_owner=Path("crates/wbd-engine/src/v4_owner_crypto.rs").read_text()
go_product=Path("r0/go_overlay/internal/realityfront/bridge_v4_linux_client_product.go").read_text()
go_bridge=Path("r0/go_overlay/internal/realityfront/bridge_v4_embedded_android.go").read_text()
assert 'wbd_m0_embedded_go_normal_startup_padding_set' in rust_m4 and 'wbd_m0_embedded_go_normal_startup_padding_counters' in rust_m4
assert 'wbd_m0_embedded_go_normal_startup_padding_set' in go_bridge and 'wbd_m0_embedded_go_normal_startup_padding_counters' in go_bridge
assert 'bridge.configureNormalStartupPadding(cold.StartupPaddingMode(),p.cfg.OuterIPMTU)' in go_product
assert 'policy.propose(&slab.writable()[14..14+n],ms,room)' in rust_m4
assert 'startup_padding_copied_bytes.fetch_add(' in rust_m4
assert 'self.seal_normal_off_one_padded(' in rust_owner
print("ANDROID_B11A_ORIGINAL_GO_RUST_M4_STARTUP_PADDING_NATIVE_SOURCE_WIRING_PASS")
# B11b: real signed Android App -> original protected Go/Rust M4, no Java DATA.
assert 'startupPaddingModes.setAdapter(new ArrayAdapter' in a
assert 'request.putExtra("startup_padding",paddingMode)' in a
assert 'intent.getStringExtra("startup_padding")' in s
assert 'launchCommand(code,net,peerForGo,sni,user,port,requestedOuterMTU,recordCipher,requestedTunQueue,paddingMode' in s
assert 'cnSplitDNS,requestedOuterMTU,recordCipher,requestedTunQueue,paddingMode,fecMode,fecProfile,directCIDRs,physicalDnsIPv4,nativeHealthSeconds);' in s
assert 'pair(args,"--startup-padding",paddingMode)' in argv
assert 'startupPadding:=flags.String("startup-padding","off"' in cold
print("ANDROID_B11B_APP_GO_M4_PROTECTED_STARTUP_PADDING_SOURCE_WIRING_PASS")
# B12a: original M1 RX/moved M3 opener, no independent cipher or Go APPLIED.
fec_entry=Path("crates/wbd-engine/src/v4_embedded_go.rs").read_text()
fec_owner=Path("crates/wbd-engine/src/v4_owner_crypto.rs").read_text()
fec_worker=Path("crates/wbd-engine/src/v4_android_original_m4.rs").read_text()
fec_go=Path("r0/go_overlay/internal/realityfront/bridge_v4_fixed_pending_android.go").read_text()
assert "Fec2LiveRx::from_authenticated_scope(" in fec_entry
assert "Some((exact,blocks,0u64))" in fec_entry
assert "*applied=0;blocks.stop();" in fec_entry
assert "pub(crate) fn drain_windows_authenticated_fec2" in fec_owner
assert ".open_unique_with_fec2_after_admission_in_place(" in fec_owner
assert "Ok(record) if matches!(record.kind,2|3)" in fec_owner
assert "owner.drain_windows_authenticated_fec2(" in fec_worker
assert "blocks.accept_authenticated(*exact,kind,payload,at)" in fec_worker
assert "tun.write_authenticated_ip(ip).ok()==Some(ip.len())" in fec_worker
assert "let fixed_pending=e.android_fec2_pending;" in fec_worker
assert "if !fixed_pending.is_some_and(|(profile,rev)|" in fec_worker
assert "exact.negotiated_features!=7" in fec_worker
assert "if *applied==0||exact.negotiated_features!=7" not in fec_worker
assert "stats.fec2_unique_symbols.fetch_add(1,Ordering::Relaxed)" in fec_worker
assert "if let Some(report)=control.low_rate_quality{" in fec_worker
assert "q.accept_report(report,at);" in fec_worker
assert "control.low_rate_signal.is_some()" in fec_worker
assert "!(e.protected_features==3||fixed_ready)" in fec_worker
assert "let fixed_ready=e.protected_features==7&&" in fec_worker
# B12bc: Go PENDING now reaches real Android Rust FFI but never APPLIED.
assert "C.wbd_m0_embedded_go_fixed_stage_pending(" in fec_go
assert "C.wbd_m0_embedded_go_fixed_pending_readback(" in fec_go
assert "originalAndroidFixedM4Counters()" in fec_go
assert 'runtime.GOOS=="android" &&' in Path(
    "r0/go_overlay/internal/realityfront/bridge_v4_linux_client_product.go"
).read_text()
print("ANDROID_B12A_ORIGINAL_SINGLE_REPLAY_FEC2_RX_TUN_CLOSED_SOURCE_PASS")
# Native Fixed source & parity use original M1/M3 with actual RAW-copy proof.
assert "fn send_android_fixed_source(" in fec_worker
assert "fn send_android_fixed_due(" in fec_worker
assert "stream.offer_source(slab,14..14+n,at" in fec_worker
assert "wbd_codec::fec_v2::source_into(" in fec_worker
assert "stream.poll_parity_quanta(at,1," in fec_worker
assert "e.owner.seal_fec2_product_one(" in fec_worker
assert "send_staged(e,raw,stats,storage,scratch,at)==Some(pn)" in fec_worker
assert "e.android_fec2_tx=Some(stream);" in fec_worker
assert "!(e.protected_features==3||fixed_ready)" in fec_worker
assert "let fixed_ready=e.protected_features==7&&" in fec_worker
assert "fn wbd_m0_embedded_go_fixed_stage_pending(" in fec_worker
assert "fn wbd_m0_embedded_go_fixed_pending_readback(" in fec_worker
assert "fn wbd_m0_embedded_go_fixed_m4_counters(" in fec_worker
assert "if out.is_null()||len!=9{return INVALID}" in fec_worker
assert "originalAndroidFixedM4Counters()([9]uint64,error)" in fec_go
assert "fn send_android_fixed_quality_due(" in fec_worker
assert "fn wbd_m0_embedded_go_public_fec2_mature_quality(" in fec_worker
assert "super::original_fixed_mature_snapshot(q,stream)" in fec_worker
assert "original_fixed_mature_snapshot(q,stream)" in fec_entry
assert 'C.wbd_m0_embedded_go_public_fec2_mature_quality(' in go_bridge
assert "q.settle_batch(&[(wbd_types::RecordPn(pn),0)]" in fec_worker
assert "q.next_signal(next_pn,at)" in fec_worker
assert "q.complete_signal(signal,sent,at)" in fec_worker
assert "q.accept_report(report,at);" in fec_worker
assert "if q.counters[10]>before{" in fec_worker
# B19: the original M3/PLAN027 Quality must refer to THIS
# revision's real copied source and repair, never the old global B13 sums.
assert "q.counters[1],positive_baseline," in fec_worker
assert "revision_source_copied,revision_repair_copied" in fec_worker
assert "e.android_fec2_revision_source_copied=true;" in fec_worker
assert "if rev==revision{e.android_fec2_revision_repair_copied=true}" in fec_worker
assert "*_applied=revision;" in fec_worker
assert "e.quality_tx=Some(OriginalQualityTx::new(" in fec_worker
assert "e.android_fec2_pending.is_some()||e.android_fec2_tx.is_some()" in fec_worker
assert "e.auto_low_rate_mode || e.server_side" in fec_entry
assert "fn original_fixed_quality_requires_copied_source_not_repair_or_uncertain()" in fec_entry
# The original Go/Rust Fixed APPLIED readback cannot be driven by receipt counts.
assert "let actual=e.android_fec2_rx.as_ref()" in fec_worker
assert "u32::from(*rev==r)" in fec_worker
assert "if let Some(stream)=e.android_fec2_tx.as_mut(){stream.stop()}" in fec_entry
assert "e.android_fec2_pending=None;" in fec_entry
print("ANDROID_B12BC_FIXED_ORIGINAL_SOURCE_PARITY_RAW_PENDING_CLOSED_SOURCE_PASS")
print("ANDROID_B12D_REAL_PENDING_FIRST_M3_REVERSE_QUALITY_SOURCE_PASS")
print("ANDROID_B13_ORIGINAL_FIXED_PLAN027_MATURE_M2_CAUSAL_SOURCE_PASS")
mtu_owner=Path("crates/wbd-engine/src/v4_owner_crypto.rs").read_text()
assert "fn android_frame_budget_for(" in mtu_owner
assert "fec:AndroidFec::FixedOff" not in mtu_owner
assert "AndroidFec::V3Fec2Fixed" in mtu_owner
assert "pub(crate) fn android_fixed_frame_budget(" in mtu_owner
assert "e.owner.android_fixed_frame_budget(s.mtu)" in fec_worker
assert "e.owner.android_fixed_frame_budget(scope.mtu)" in fec_worker
assert "e.staged_count==0" in fec_worker
assert "android_fixed_cold_and_m4_reservation_share_exact_14_bytes" in Path(
    "crates/wbd-engine/src/v4_mtu_budget_ffi.rs"
).read_text()
# B17/B19 original Go Fixed/Auto -> native FEC2, Normal default.
client=Path("r0/go_overlay/internal/realityfront/bridge_v4_linux_client_product.go").read_text()
assert 'v4ProductFecEnabled(p.cfg.FECMode)&&p.cfg.StartupPaddingMode!=0' in client
assert 'runtime.GOOS!="android"||mode==FecV2Off' in client
assert 'if p.fec!=nil&&(runtime.GOOS!="android"||mode==FecV2Auto)' in client
assert 'String fecMode=fecModes.getSelectedItem().toString()' in a
assert 'request.putExtra("fec_mode",fecMode);' in a
assert 'request.putExtra("fec_profile",fecProfile);' in a
assert 'intent.getStringExtra("fec_mode")' in s
assert 'intent.getIntExtra("fec_profile",1)' in s
assert 'pair(args,"--mode",productMode);' in argv
assert 'pair(args,"--fec-profile",Integer.toString(fecProfile))' in argv
assert '(cfg.gameLanes!=0&&cfg.gameLanes!=2&&cfg.gameLanes!=4)||cfg.mixedModes||' in cold
assert 'if cfg.gameLanes!=0&&(cfg.startupPaddingMode!=0||' in cold
assert 'C.wbd_m0_embedded_go_public_fec2_mature_quality(' in go_bridge
assert 'return b.verifyOriginalAndroidAutoPending()' in go_bridge
assert 'C.wbd_m0_embedded_go_fixed_pending_readback(' in fec_go
assert 'new String[]{"normal","fec-fixed","fec-auto","game2","game4","game2-fixed","game4-fixed"}' in a
assert '"fec-auto"' in argv
assert 'e.android_fec2_auto_requested.or(e.android_fec2_pending)' in fec_worker
assert 'stream.quiescent_change(next_profile,next_rev,at).is_ok()' in fec_worker
assert 'stream.prior_parity_revision()' in fec_worker
assert 'plan.offset==0' in fec_worker
assert 'super::android_auto_report_is_revision_positive(' in fec_worker
assert 'android_auto_report_is_revision_positive(' in fec_entry
print("ANDROID_B19_ORIGINAL_AUTO_ROOT_APP_M4_QUALITY_REVISION_PASS")
print("ANDROID_B17_FIXED_ORIGINAL_GO_ROOT_APP_OPTIN_SOURCE_PASS")
# B31 Root original single/selected group/all-app policy must pass
# the same Go-authenticated physical peer IPv4 to the real FIB owner.
b31_android=Path("r0/go_overlay/internal/v4productcli/android_root_route_android.go").read_text()
b31_single=Path("r0/go_overlay/internal/v4productcli/rootjournal/journal.go").read_text()
b31_group=Path("r0/go_overlay/internal/v4productcli/rootjournal/group.go").read_text()
assert b31_android.count('ServerIP:c.peerIP.String()')==3
for source in (b31_single,b31_group):
 assert 'peerThrowArgs("add",original.ServerIP)' in source
 assert 'peerThrowArgs("del",p.ServerIP)' in source
print("ANDROID_B31_ORIGINAL_ROOT_UID_PEER_EXCEPTION_WIRING_SOURCE_PASS")
# B33 one original Go Android Root owner, 4 selected CIDR direct
# FIB throws in all 3 existing UID routes, with no new raw/tun worker.
b33_go=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
b33_root=Path("r0/go_overlay/internal/v4productcli/android_root_route_android.go").read_text()
b33_route=Path("r0/go_overlay/internal/v4productcli/rootjournal/direct.go").read_text()
b33_ui=Path("android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
b33_svc=Path("android/root-app/src/org/wbdnext/rootclient/RootClientService.java").read_text()
b33_argv=Path("android/root-app/src/org/wbdnext/rootclient/OriginalGoCommandArgs.java").read_text()
assert 'flags.String("android-direct-cidrs"' in b33_go and 'rootjournal.ParseDirectCIDRs(' in b33_go
assert b33_root.count('DirectCIDRs:append([]string(nil),c.androidDirectCIDRs...)')==3
assert 'routeWithDirect(' in b33_route and 'directArgs(' in b33_route
assert 'direct_cidrs' in b33_ui and 'direct_cidrs' in b33_svc
assert '--android-direct-cidrs' in b33_argv and 'RootDirectIPv4.canonicalCSV(' in b33_argv
print("ANDROID_B33_ORIGINAL_ROOT_IP_DIRECT_CIDR_THREE_UID_SCOPES_SOURCE_PASS")
# B34 original all-app UID exclusion over 20 user profiles, with exact
# installed package+UID revalidation before every original Go/Root grant.
b34_scope=Path("android/root-app/src/org/wbdnext/rootclient/AllAppRouteScope.java").read_text()
b34_policy=Path("android/root-app/src/org/wbdnext/rootclient/AllAppUIDPolicy.java").read_text()
b34_settings=Path("android/root-app/src/org/wbdnext/rootclient/RootConnectionSettings.java").read_text()
assert 'AllAppUIDPolicy.excluded(Process.myUid(),managerUIDs,bypassUIDs)' in b34_scope
assert 'info.uid!=bypassUIDs[i]' in b34_scope
assert 'new TreeSet<>(reserved)' in b34_policy
assert '"bypass_packages"' in b33_ui and '"bypass_uids"' in b33_ui
assert '"bypass_packages"' in b33_svc and '"bypass_uids"' in b33_svc
assert 'watchedAllAppPackages(managerPackages,bypassPackages)' in b33_svc
assert 'p.setProperty("bypass_count"' in b34_settings
print("ANDROID_B34_ALL_APP_BYPASS_REAL_UID_FIB_AND_PRESET_SOURCE_PASS")
# B34 physical DNS app-selected IPv4 is set only on original Go
# authenticated Rust M4 generation, on the EXISTING bound UDP socket.
b34_bridge=Path("r0/go_overlay/internal/realityfront/bridge_v4_embedded_android.go").read_text()
b34_product=Path("r0/go_overlay/internal/realityfront/bridge_v4_linux_client_product.go").read_text()
b34_platform=Path("crates/wbd-platform/src/android_root_io.rs").read_text()
b34_rust=Path("crates/wbd-engine/src/v4_embedded_go.rs").read_text()
b34_m4=Path("crates/wbd-engine/src/v4_android_original_m4.rs").read_text()
assert '"physical_dns_upstream"' in b33_ui and '"physical_dns_upstream"' in b33_svc
assert '--android-physical-dns-upstream-ipv4' in b33_argv
assert 'flags.String("android-physical-dns-upstream-ipv4"' in b33_go
assert 'dnsnative.ParsePhysicalDNSUpstreamIPv4(' in b33_go
assert 'setAndroidPhysicalDNSUpstream(upstream)' in b34_product
assert 'wbd_m0_embedded_go_android_physical_dns_upstream_set' in b34_bridge
assert 'wbd_m0_embedded_go_android_physical_dns_upstream_effective' in b34_bridge
assert 'pub unsafe extern "C" fn wbd_m0_embedded_go_android_physical_dns_upstream_set(' in b34_rust
assert 'e.android_dns_physical_upstream' in b34_m4
assert 'ip_be:u32::from_ne_bytes(upstream_ipv4)' in b34_platform
assert 'android_setsocknetwork(' in b34_platform
print("ANDROID_B34_ORIGINAL_RUST_M4_BOUND_PHYSICAL_DNS_IPV4_SOURCE_PASS")
# B29: default Tunnel DNS must not reject Fixed/Auto feature7 before M4.
b29_go=Path("r0/go_overlay/internal/realityfront/bridge_v4_embedded_android.go").read_text()
b29_rust=Path("crates/wbd-engine/src/v4_embedded_go.rs").read_text()
b29_route=Path("crates/wbd-engine/src/v4_android_dns_route.rs").read_text()
# The 4th pre-existing match belongs to native FEC quality readback,
# not a newly permitted DNS cold grant.
assert b29_go.count('b.protectedFeatures!=(v4RequiredFeatures|v4FeatureFEC2)')==4
# B34 keeps all prior 3 DNS M4 cold gates and adds one exact authenticated
# physical UDP53 upstream setter; this MUST be the fourth cold-ready check.
assert b29_rust.count('!android_dns_original_m4_ready(&e)')==4
assert 'original_m4_dns_feature_allowed(' in b29_rust
assert 'features==3||(features==7&&fec2_rx_ready)' in b29_route
assert 'tunnelDNS.setChecked(true)' in a
assert 'v4ConfigureProductFec(bridge,mode,p.cfg.FECProfile,cold)' in client
assert 'let fixed_requested=e.protected_features==7' in Path(
    "crates/wbd-engine/src/v4_android_original_m4.rs").read_text()
print("ANDROID_B29_FIXED_AUTO_NORMAL_SAME_ORIGINAL_M4_DNS_COLD_WIRING_SOURCE_PASS")
assert 'privateText("wbd-route.secret",key+"\\n")' in a, "the original Go still reads only the canonical 32B hex secret file"
# Verified device bug: AOSP ContextImpl.MODE_PRIVATE can create 0660,
# original Go readPrivateArgFile intentionally rejects any group bits.
writer=Path("android/root-app/src/org/wbdnext/rootclient/RootPrivateCredentialFiles.java").read_text()
contract=Path("android/root-app/src/org/wbdnext/rootclient/RootPrivateCredentialContract.java").read_text()
assert 'RootPrivateCredentialFiles.write(this,file,text);' in a
assert 'openFileOutput(file,Context.MODE_PRIVATE)' not in a
for required in ('Os.open(path.getAbsolutePath()', 'OsConstants.O_NOFOLLOW',
  'OsConstants.O_CLOEXEC', 'Os.fchmod(fd,RootPrivateCredentialContract.OWNER_ONLY)',
  'verifyStat(Os.fstat(fd)', 'Os.lstat(', 'verifyAtStart(Context ctx,boolean hasCA)'):
 assert required in writer, required
assert '(mode&0777)==OWNER_ONLY' in contract and 'st.st_nlink' in writer
assert 'RootPrivateCredentialFiles.verifyAtStart(this,hasCA)' in s
assert 'APP_PRIVATE_CREDENTIALS_UNSAFE' in s
assert 'APP_PRIVATE_CREDENTIALS_0600_VERIFIED' in s
assert 'st.Mode().Perm()&0077!=0' in cold, "never relax original Go private read check"

assert 'String key=RootRouteKeyCache.resolve(this,sni,keyInput);' in a
assert 'RootRouteKeyV2.legacyHex(supplied)' in Path("android/root-app/src/org/wbdnext/rootclient/RootRouteKeyCache.java").read_text()
assert 'file.readFully()' in Path("android/root-app/src/org/wbdnext/rootclient/RootRouteKeyCache.java").read_text()
assert 'Os.chmod(destination.getAbsolutePath(),0600)' in Path("android/root-app/src/org/wbdnext/rootclient/RootRouteKeyCache.java").read_text()
assert 'AtomicFile' in Path("android/root-app/src/org/wbdnext/rootclient/RootRouteKeyCache.java").read_text()
assert 'PBKDF2WithHmacSHA256' in Path("android/root-app/src/org/wbdnext/rootclient/RootRouteKeyV2.java").read_text()
cold=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
go=Path("r0/go_overlay/internal/v4productcli/android_root_route_android.go").read_text()
assert 'rootjournal.NewGroup(' in go and 'V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED uids=' in go
assert 'rootjournal.NewAllApps(' in go and 'V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED mode=all_apps' in go
assert 'ServerIP:c.peerIP.String()' in go
assert 'V4_PUBLIC_ANDROID_PEER_THROW_ROUTE_READBACK role=client' in go
assert 'SERVER_PEER_THROW_PRIVATE_FIB_READBACK' in s
assert 'androidRouteAllApps' in cold and 'android-route-all-apps' in cold
# A31: original Go Run's parse rejection must emit only the fixed
# allowlisted category and never return dynamic error strings to the report.
assert 'originalAndroidColdParseClass(err)' in cold
assert 'V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=%s' in cold
assert 'log.Printf("V4_PUBLIC_ANDROID_GO_ARGS_REJECTED role=client class=%s"' in cold
report=Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReport.java").read_text()
receipt=Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java").read_text()
for field in (
  "FLAG_SYNTAX", "PASSWORD_FILE", "ROUTE_KEY_FILE", "ROUTE_KEY_VALUE",
  "INSTALLATION_ID", "CN_GEOSITE_FILE", "TLS_CA_FILE",
  "ALL_APP_EXCLUSIONS", "ANDROID_NETWORK_SCOPE", "PEER_ADDRESS",
  "REQUIRED_COLD_SETTINGS", "POLICY", "OTHER"):
 assert ("ORIGINAL_GO_PARSE_"+field) in s and ("ORIGINAL_GO_PARSE_"+field) in receipt
 assert ("ORIGINAL_GO_ARGUMENT_PARSE_REJECTED_"+field) in report
assert "return \"ORIGINAL_GO_ARGUMENT_PARSE_REJECTED\";" in report

allapp=Path("r0/go_overlay/internal/v4productcli/rootjournal/allapps.go").read_text()
assert 'func NewAllApps(' in allapp and 'requireReady(original)' in allapp and 'readOwnedJournalVersion(' in allapp
assert 'AllAppIDMin = 10000' in allapp and 'AllAppIDMax = 19999' in allapp
assert 'allMaxUserProfiles = 20' in allapp and 'ExcludedAppIDs' in allapp
assert 'peerThrowArgs("add",original.ServerIP)' in allapp
assert 'peerThrowArgs("del",p.ServerIP)' in allapp
assert 'legacyAllAppsVersion = 3' in allapp
assert 'Intent.ACTION_CREATE_DOCUMENT' in a, "system SAF safe-report export"
assert 'RootDiagnosticReport.build(getFilesDir()' in a

j=Path("r0/go_overlay/internal/v4productcli/rootjournal/group.go").read_text()
assert 'func NewGroup(' in j and 'readOwnedJournalVersion(' in j and 'groupRuleState(' in j
# B2b source-lock: an actual signed asset is verified and handed as an
# app-private path to the ORIGINAL Go cold parser, not a Java fake packet
# handler or claimed Android DNS network state.
payload=Path("android/root-app/src/org/wbdnext/rootclient/NativePayload.java").read_text()
assert 'PINNED_CN_SHA256' in payload and 'cn-geosite-provenance.json' in payload
assert '"wbd-cn-geosite.txt",PINNED_CN_SHA256,6000000' in payload
assert 'new NativePayload(go,rust,cn,source,executable)' in payload
assert 'armAssets==x86Assets' in payload, 'only one signed ABI allowed'
assert '(!armAssets&&m.optBoolean("release",true))' in payload, 'x86 must be CI-only'
assert 'signed native ABI not supported by OS' in payload
assert 'libwbd_engine-' in payload and 'wbd-v4-client-' in payload, 'one original ABI-selected Go/Rust'
assert 'ownerExecutable=code.executableName' in s, 'exact original GO executable at Stop'
assert 'nativeCode.cnGeosite.getAbsolutePath()' in s and '"--android-cn-geosite-file"' in argv
cold=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
assert 'cnGeositeFile:=flags.String("android-cn-geosite-file"' in cold
assert 'dnsnative.ReadPinnedCNFile(*cnGeositeFile)' in cold
assert 'dns_capture=NOT_CONNECTED' in cold
assert 'peerHost:=flags.String("peer-host"' in cold
assert 'dnsnative.ResolveBootstrapIPv4WithUpstream(' in cold
assert 'dnsnative.NewAndroidPhysicalDNSDialerWithUpstream(' in cold
assert 'cfg.androidPhysicalDNSUpstream)' in cold
assert 'ANDROID_B35_PEER_HOST_CUSTOM_PHYSICAL_DNS_COLD_ARGV_HOST_PASS' in Path(
    "android/root-app/ci/OriginalGoCommandArgsTest.java").read_text()
assert 'V4_PUBLIC_ANDROID_SERVER_BOOTSTRAP_PHYSICAL_RESOLVED' in cold
typed=Path("r0/go_overlay/internal/v4productcli/dnsnative/cn_rules.go").read_text()
assert 'syscall.O_NOFOLLOW|syscall.O_NONBLOCK' in typed
assert 'st.Mode().Perm()!=0600' in typed
assert 'return ReadPinnedCN(f)' in typed
print("ANDROID_B2B_SIGNED_GEOSITE_TO_ORIGINAL_GO_COLD_SOURCE_GATE_PASS")
m=Path("android/root-app/AndroidManifest.xml").read_text()
assert '<queries>' in m and '<uses-permission android:name="android.permission.QUERY_ALL_PACKAGES"' in m, "B32 full current-user package picker"
catalog=Path("android/root-app/src/org/wbdnext/rootclient/InstalledAppCatalog.java").read_text()
assert 'Intent.ACTION_SEND' in catalog and 'share.setType("text/plain")' in catalog
assert 'Intent.ACTION_VIEW' in catalog and 'Intent.CATEGORY_BROWSABLE' in catalog
assert 'InstalledAppCatalog.discoverable(this)' in a
assert 'TreeSet<String> available=visibleNames(pm)' in catalog
assert 'ApplicationInfo app=pm.getApplicationInfo(name,0)' in catalog
assert 'android.intent.action.SEND' in m and 'android.intent.action.VIEW' in m
assert 'android:mimeType="text/plain"' in m and 'android:scheme="https"' in m
assert 'pm.getInstalledApplications(0)' in catalog
assert 'InstalledAppTarget.eligible(name,app.uid,Process.myUid()' in catalog
assert 'SelectedAppGroup.matchesReceipt(' in catalog
print("ANDROID_B32_INSTALLED_ORDINARY_APP_GAME_PICKER_ORIGINAL_UID_HOST_SOURCE_PASS")
# The exact POSIX read arity must preserve kernel starttime for both
# existing old 2-field receipts and current 3-field receipts.
import subprocess,tempfile
with tempfile.TemporaryDirectory() as td:
    for payload,expected in (("123 9876","123|9876|"),
                             ("123 9876 abcdef","123|9876|abcdef")):
        p=Path(td)/"owner.pid"
        p.write_text(payload+chr(10))
        cmd='read pid start generation < "$1"; printf "%s|%s|%s" "$pid" "$start" "$generation"'
        result=subprocess.run(["sh","-c",cmd,"sh",str(p)],capture_output=True,text=True,check=True)
        assert result.stdout==expected,(payload,result.stdout)
print("ANDROID_ROOT_OWNED_PID_2_AND_3_FIELD_PARSE_PASS")
# Same-source fixed-enum, credential-free diagnostic receipts; never
# echo arbitrary native stdout and never count a Stop TERM as joined Stop.
assert 'OriginalGoMilestones.matches(' in s
assert 'ROOT_OR_NATIVE_EXIT_' in s and 'SYNACK_PRE_AUTH' in s
assert 'RootDiagnosticReceipt.Event.ORIGINAL_GO_TUN_KERNEL_CONFIGURED' in s
assert 'RootDiagnosticReceipt.Event.ORIGINAL_GO_RAW_SOCKET_READY' in s
assert 'RootDiagnosticReceipt.Event.ORIGINAL_GO_TCP_SYNACK_SEEN' in s
assert 'WBD_ROOT_DIAG' in s
assert 'RootDiagnosticReceipt.Event.NATIVE_M4_AND_UID_READY' in s
assert 'RootDiagnosticReceipt.Event.STOP_SIGNAL_ACCEPTED' in s
assert 'RootDiagnosticReceipt.Event.ORIGINAL_GO_RUST_STOP_JOINED' in s
assert 'RootDiagnosticReceipt.Event.AUTHENTICATED_LEASE_OS_READBACK' in s
assert 'RootDiagnosticReceipt.Event.OWNER_CLEANUP_FINISHED' in s
assert 'Log.i("WBD_ROOT_DIAG",event.name())' in s
accept=Path("android/root-app/ci/device_first_run.py").read_text()
assert '"real_android_linux_tls_and_data_e2e": "NOT_RUN"' in accept
assert '"original_go_rust_joined_stop":' in accept
assert '"ORIGINAL_GO_RUST_STOP_JOINED"' in accept
for cold_stage in ("ORIGINAL_GO_TUN_KERNEL_CONFIGURED",
                   "ORIGINAL_GO_RAW_SOCKET_READY",
                   "ORIGINAL_GO_TCP_SYNACK_SEEN"):
    assert cold_stage in accept, "first-run receipt must retain native cold-stage codes"
assert '"AUTHENTICATED_LEASE_OS_READBACK"' in accept
assert 'FIB table does not exist' in accept
assert '"wbdv40"' in accept
assert 'sudo' not in accept and 'pkill' not in accept
print("ANDROID_ROOT_DEVICE_DIAGNOSTIC_AND_OPERATOR_BUNDLE_HOST_PASS")

# A33 cold diagnostics must observe original stage sites, never fabricate TLS
# or promote a candidate SYNACK into an accepted FakeTCP association.
go_product=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
go_admission=Path("r0/go_overlay/internal/realityfront/admission_v4.go").read_text()
assert go_product.index('V4_PUBLIC_ANDROID_ORIGINAL_ASSOC_ESTABLISHED role=client') > go_product.index('waitForOriginalColdSYN(dialCtx,assoc)')
assert 'V4_PUBLIC_ANDROID_TLS_HANDSHAKE_ATTEMPTED role=client' in go_admission
assert go_admission.index('V4_PUBLIC_ANDROID_TLS_HANDSHAKE_VERIFIED role=client') > go_admission.index('handshakeClientConn(ctx,conn,tlsCfg)')
assert go_admission.index('V4_PUBLIC_ANDROID_PROTECTED_REPLY_PARSED role=client') > go_admission.index('v4ReadReply(client,req)')
assert go_admission.index('V4_PUBLIC_ANDROID_ADMISSION_VERIFIED role=client') > go_admission.index('v4ColdSnapshot(result,extension.Epoch')
assert 'v4AndroidColdFailureClass(err)' in go_admission
for event in ("ORIGINAL_GO_ASSOC_ESTABLISHED","ORIGINAL_GO_TLS_HANDSHAKE_ATTEMPTED",
              "ORIGINAL_GO_TLS_HANDSHAKE_VERIFIED","ORIGINAL_GO_ADMISSION_VERIFIED",
              "ORIGINAL_GO_PROTECTED_REPLY_FAILED_AUTH_REJECTED"):
 assert event in s and event in receipt and event in report
assert 'SYNACK_CANDIDATE_ASSOC_NOT_PROVEN' in report
print("ANDROID_A33_ORIGINAL_COLD_TLS_NO_FAKE_WIRE_SOURCE_GATE_PASS")
# A34: actual original output/peer ingress, no fake ClientHello or no-TLS fallback.
assert 'observedEmit:=func(seg faketcp.Segment)error' in go_product
assert go_product.index('V4_PUBLIC_ANDROID_COLD_BOOTSTRAP_PAYLOAD_TX_OK role=client') > go_product.index('e:=emit(seg)')
assert 'firstPeerPayloadRX.CompareAndSwap(false,true)' in go_product
assert 'v4AndroidClassAtDeadline(err,guard.Remaining())' in go_admission
for ev in ("ORIGINAL_GO_COLD_BOOTSTRAP_PAYLOAD_TX_OK",
           "ORIGINAL_GO_COLD_RAW_PEER_PAYLOAD_RX",
           "ORIGINAL_GO_COLD_RAW_PEER_PAYLOAD_RX_NOT_OBSERVED",
           "ORIGINAL_GO_TLS_HANDSHAKE_FAILED_DEADLINE_ELAPSED_OTHER"):
 assert ev in s and ev in receipt
print("ANDROID_A34_ORIGINAL_TLS_WIRE_SOURCE_GATE_PASS")
# A35 exact 4-tuple RST suppression MUST only run on actual Android root,
# before the original SYN, with durable journal and exact Stop readback.
rst=Path("r0/go_overlay/internal/v4productcli/rstguard/guard.go").read_text()
test=Path("r0/go_overlay/internal/v4productcli/rstguard/guard_test.go").read_text()
assert go_product.index('V4_PUBLIC_ANDROID_COLD_RST_GUARD_READY role=client') < go_product.index('reauthAuthorized:=false')
assert go_product.index('reauthAuthorized:=false') < go_product.index('runClient(ctx,cfg,')
for required in ('--sport','--dport','--tcp-flags','--comment','-o','-s','-d',
                 'O_NOFOLLOW','O_EXCL','LOCK_NB','ErrCleanup','DropCounter'):
 assert required in rst
assert 'FakeTCP' in test or 'TestScopedRSTGuard' in test
for marker in ("ORIGINAL_GO_COLD_RST_GUARD_READY",
               "ORIGINAL_GO_COLD_RST_GUARD_STOP_UNVERIFIED",
               "ORIGINAL_GO_COLD_RST_GUARD_FAILED_IPTABLES_UNAVAILABLE"):
 assert marker in s and marker in receipt and marker in report or marker.endswith("READY")
# Every original Android/Linux server assembly must copy the same pure-Go
# guard package. Missing x86 D2-S0 donor copy caused first A35 D2-S0 FAIL.
for assembler in ("android/root-native/build-source-locked.sh",
                  "android/root-native/ci/linux-original-oracle.sh",
                  "android/root-app/ci/x86-original-linux-server-prep.sh"):
    text=Path(assembler).read_text()
    assert 'cp r0/go_overlay/internal/v4productcli/rstguard/*.go legacy/internal/v4productcli/rstguard/' in text
    assert 'go test -count=1 ./internal/v4productcli/rstguard' in text
print("ANDROID_A35_THREE_ORIGINAL_GO_DONOR_ASSEMBLIES_SOURCE_LOCKED_PASS")
print("ANDROID_A35_SCOPED_RST_GUARD_NO_GLOBAL_FIREWALL_SOURCE_PASS")
# A36 Restore only runs source-locked original-Go exact journal cleanup.
assert 'RootClientService.RESTORE' in Path("android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
assert '--android-recover-owned-root' in Path("android/root-app/src/org/wbdnext/rootclient/RootRecoveryCommand.java").read_text()
assert 'rootjournal.RecoverOwned(' in go_product and 'rstguard.RecoverOwned(' in go_product
assert 'flags.Bool("tls-verify-server",false' in go_product
assert 'VerifyServer:c.tlsVerifyServer' in go_product
assert 'c.tlsVerifyServer=role=="client"&&*verifyTLS' in go_product
assert 'tlsVerifyServer.setChecked(false)' in Path("android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
assert 'request.putExtra("tls_verify_server",verifyTLS)' in Path("android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
assert 'args.add("--tls-verify-server")' in argv
for ev in ("ORIGINAL_GO_TLS_CERT_VERIFY_DISABLED","ORIGINAL_GO_TLS_CERT_VERIFY_ENABLED"):
 assert ev in s and ev in receipt
print("ANDROID_A37_MAIN_DEFAULT_TLS_CERT_VERIFY_OFF_SOURCE_PASS")
# A38: prove no second forced verify in the REAL protected admission;
# the user's A37 device showed disabled at parse but unknown CA at TLS.
assert 'tlsCfg.VerifyServer=true' not in go_admission
assert 'tlsCfg:=cfg.TLS' in go_admission
assert 'V4_PUBLIC_ANDROID_TLS_CERT_VERIFY_EFFECTIVE role=client class=DISABLED' in go_admission
for ev in ('ORIGINAL_GO_TLS_CERT_VERIFY_EFFECTIVE_DISABLED',
           'ORIGINAL_GO_TLS_CERT_VERIFY_EFFECTIVE_ENABLED'):
 assert ev in s and ev in receipt
print("ANDROID_A38_NO_ORIGINAL_ADMISSION_CERT_OVERRIDE_SOURCE_GATE_PASS")
# UI plaintext secrets never go to SharedPreferences, Intent or logging.
store=Path("android/root-app/src/org/wbdnext/rootclient/RootEncryptedCredentialStore.java").read_text()
codec=Path("android/root-app/src/org/wbdnext/rootclient/RootSavedCredentialRecord.java").read_text()
for token in ('AndroidKeyStore','KeyGenParameterSpec','KeyProperties.BLOCK_MODE_GCM',
              'getNoBackupFilesDir()','AtomicFile','Os.fchmod','0600'):
 assert token in store
for token in ('AES/GCM/NoPadding','updateAAD(AAD)','cipher.doFinal','Arrays.fill'):
 assert token in codec
assert 'RootEncryptedCredentialStore.save(this,secret,keyInput)' in a
assert 'RootStartCredentialSave.attempt(' in a
assert 'UI_START_TAPPED' in a and 'UI_START_DISPATCHED' in a
assert 'UI_START_VALIDATION_REJECTED' in a and 'UI_START_DISPATCH_FAILED' in a
assert 'UI_CREDENTIAL_SAVE_FAILED' in a
assert 'RootEncryptedCredentialStore.load(this)' in a
assert 'RootEncryptedCredentialStore.clear(this)' in a
assert 'password.setText("")' in a and 'routeKey.setText("")' in a
assert 'request.putExtra("password"' not in a and 'request.putExtra("route_key"' not in a
assert 'cipher.init(Cipher.ENCRYPT_MODE,key);' in codec
assert 'cipher.getIV()' in codec
assert 'cipher.init(Cipher.ENCRYPT_MODE,key,new GCMParameterSpec' not in codec
# A40 real original post-auth transitions, not a synthetic lease.
postauth=Path("r0/go_overlay/internal/realityfront/bridge_v4_linux_client_product.go").read_text()
androidbridge=Path("r0/go_overlay/internal/realityfront/bridge_v4_embedded_android.go").read_text()
for stage in ("COLD_OK","DETACH_OK","NATIVE_COMMIT_OK","LEASE_FIELD_OK","LEASE_OS_OK","NATIVE_IP_BOUND","UNDERLAY_OK","RAW_ATTACHED","TUN_ATTACHED","M4_STARTED","COLD_FAILED","DETACH_FAILED","NATIVE_PREPARE_FAILED","NATIVE_COMMIT_FAILED","NATIVE_OTHER_FAILED","LEASE_FIELD_FAILED","LEASE_ADD_FAILED","LEASE_DEL_FAILED","LEASE_READBACK_FAILED","LEASE_MISMATCH","LEASE_OS_FAILED","NATIVE_IP_BIND_FAILED","MTU_FAILED","UNDERLAY_FAILED","RAW_FAILED","TUN_FAILED","HEALTH_FAILED","M4_START_FAILED","UID_ROUTE_FAILED"):
 assert f'ORIGINAL_GO_POSTAUTH_{stage}' in s
 assert f'ORIGINAL_GO_POSTAUTH_{stage}' in receipt
 assert f'"{stage}"' in (postauth+go_product)
assert 'Operation:"original_native_prepare"' in androidbridge
assert 'Operation:"original_native_commit"' in androidbridge
assert 'V4_PUBLIC_ANDROID_POSTAUTH role=client class=%s' in postauth
assert 'V4_PUBLIC_ANDROID_POSTAUTH role=client class=%s' in go_product
# A41 Android native kernel lease readback uses the same getifaddrs
# interface API already proven on real device physical Network. This
# avoids Android-only external ip JSON "addr" parsing after successful add/del.
assert 'if runtime.GOOS=="android"{\n        iface,err:=net.InterfaceByName(name)' in go_product
assert 'addrs,err:=iface.Addrs()' in go_product
assert 'return originalV4OwnedTunIPv4FromNativeAddrs(addrs)' in go_product
assert 'func originalV4OwnedTunIPv4FromNativeAddrs(addrs []net.Addr)' in go_product
assert 'TestA41AndroidOriginalOwnedTunIPv4NativeGetifaddrs' in Path("r0/go_overlay/internal/v4productcli/android_native_tun_lease_readback_linux_test.go").read_text()
assert 'ANDROID_A41_ORIGINAL_ANDROID_GETIFADDRS_LEASE32_REAL_GO_HOST_PASS' in Path("android/root-native/ci/linux-original-oracle.sh").read_text()
# A42 original-Go Android post-M4 branches; no wire or sender change.
for stage in ("COLD_RTO_STOP_FAILED","DETACH_STATE_FAILED","GO_RX_FILTER_FAILED",
              "GO_RX_FILTER_OK","GO_RX_HANDOFF_OK","UID_ROUTE_ENTERED"):
 assert f'originalAndroidPostauthGo("{stage}")' in go_product
 assert f'ORIGINAL_GO_POSTAUTH_{stage}' in s
 assert f'ORIGINAL_GO_POSTAUTH_{stage}' in receipt
 assert f'ORIGINAL_GO_POSTAUTH_{stage}' in report
# A43: only original Android client Go's obsolete RX FD is retired.
raw_owner=Path("r0/go_overlay/internal/faketcp/raw_detached_data_linux.go").read_text()
raw_test=Path("r0/go_overlay/internal/faketcp/raw_detached_data_linux_test.go").read_text()
assert 'func (e *RawIPv4Endpoint) QuiesceDetachedClientReceive() error {' in raw_owner
assert 'Code: unix.BPF_RET | unix.BPF_K, K: 0' in raw_owner
assert 'return unix.SetsockoptSockFprog(e.recvFD,' in raw_owner
assert 'raw.QuiesceDetachedClientReceive()' in go_product
assert 'raw.ExcludeDetachedData(flow.PeerIP,flow.PeerPort)' in go_product
assert 'TestA43OriginalAndroidDetachedClientRXKernelQuiesce' in raw_test
assert 'ANDROID_A43_ORIGINAL_GO_CLIENT_RX_REAL_KERNEL_QUIESCE_HOST_PASS' in Path("android/root-native/ci/linux-original-oracle.sh").read_text()
# A44 original real M4 worker business counters + non-mutating UID route-get.
rust=Path("crates/wbd-engine/src/v4_android_original_m4.rs").read_text()
bridge=Path("r0/go_overlay/internal/realityfront/bridge_v4_embedded_android.go").read_text()
aroute=Path("r0/go_overlay/internal/v4productcli/android_root_route_android.go").read_text()
parser=Path("r0/go_overlay/internal/v4productcli/rootjournal/effective_route.go").read_text()
assert 'pub unsafe extern "C" fn wbd_m0_embedded_go_loop_business_receipts(' in rust
assert 'originalAndroidBusinessReceipts()' in bridge
assert 'wbd_m0_embedded_go_loop_dns_ingress_observed' in bridge
for x in ('tun_ipv4_admitted.fetch_add(1','tun_ipv4_rejected.fetch_add(1',
          'business_raw_copied.fetch_add(1','business_reverse_tun.fetch_add(u64::from(delivered)'):
 assert x in rust,x
for x in ("TUN_IPV4_SEEN","TUN_IPV4_REJECTED","APP_RAW_TX_COPIED",
          "APP_REVERSE_TUN_WRITTEN","DNS_UDP53_TUN_SEEN","DNS_TCP53_TUN_SEEN"):
 assert f'ORIGINAL_RUST_{x}' in s and f'ORIGINAL_RUST_{x}' in receipt
 assert f'V4_PUBLIC_ANDROID_BUSINESS role=client class={x}' in s
for x in ("MATCHED_TUN","MISMATCH","UNAVAILABLE"):
 assert f'ORIGINAL_GO_UID_ROUTE_GET_{x}' in s and f'ORIGINAL_GO_UID_ROUTE_GET_{x}' in receipt
 assert f'V4_PUBLIC_ANDROID_UID_ROUTE_GET role=client class={x}' in s
assert 'originalAndroidSelectedUIDRouteGet(runner,' in aroute
assert 'SelectedUIDRouteGetUsesTun(out,tun)' in aroute
assert 'func SelectedUIDRouteGetUsesTun(' in parser
assert 'TestA44OriginalUIDEffectiveRouteGetParser' in Path("r0/go_overlay/internal/v4productcli/rootjournal/effective_route_test.go").read_text()
assert 'TestA44OriginalAndroidBusinessReceiptClasses' in Path("r0/go_overlay/internal/v4productcli/android_business_witness_linux_test.go").read_text()
assert 'ANDROID_A44_ORIGINAL_RUST_BUSINESS_WITNESS_CLASSIFIER_REAL_GO_HOST_PASS' in Path("android/root-native/ci/linux-original-oracle.sh").read_text()
assert 'wbd_m0_embedded_go_loop_business_receipts' in Path("android/root-native/build-source-locked.sh").read_text()
# A45: do not mistake second-app ICMP outside selected UIDs for data-plane FAIL.
# Android original Rust callback is an actual read-only M4 worker counter,
# never shell ping, Go per-packet processing, fabricated server or UI READY.
native=Path("crates/wbd-engine/src/v4_android_original_m4.rs").read_text()
adapter=Path("r0/go_overlay/internal/realityfront/bridge_v4_embedded_android.go").read_text()
builder=Path("android/root-native/build-source-locked.sh").read_text()
goproduct=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
gotest=Path("r0/go_overlay/internal/v4productcli/android_business_witness_linux_test.go").read_text()
assert 'fn wbd_m0_embedded_go_loop_return_path_receipts(' in native
assert 'originalAndroidReturnPathReceipts()' in adapter
assert 'wbd_m0_embedded_go_loop_return_path_receipts' in builder
assert 'stats.raw_poll_ready.fetch_add(1' in native
assert 'stats.raw_parse_failed.fetch_add(1' in native
assert 'stats.raw_authenticated.fetch_add(1' in native
assert 'stats.raw_auth_rejected.fetch_add(' in native
assert 'stats.reverse_tun_write_failed.fetch_add(' in native
assert 'match head[9]' in native
for field in ('tun_icmp.fetch_add(1','tun_tcp.fetch_add(1','tun_udp.fetch_add(1'):
 assert field in native,field
assert 'TestA45OriginalAndroidReturnPathReceiptClasses' in gotest
assert 'ANDROID_A45_ORIGINAL_RETURN_PATH_AND_ICMP_CLASSIFIER_GO_HOST_PASS' in Path('android/root-native/ci/linux-original-oracle.sh').read_text()
for name in ("RAW_SOCKET_READABLE","RAW_PARSE_FAILED","RAW_PARSED",
             "RAW_AUTHENTICATED","RAW_AUTH_REJECTED","REVERSE_TUN_WRITE_FAILED",
             "TUN_ICMP_SEEN","TUN_TCP_SEEN","TUN_UDP_SEEN"):
 assert f'ORIGINAL_RUST_{name}' in s and f'ORIGINAL_RUST_{name}' in receipt
 assert f'V4_PUBLIC_ANDROID_BUSINESS role=client class={name}' in s
 assert f'"{name}"' in goproduct
# A46: copy EXACT main's already-landed Windows H2216 Linux/Android
# shared Rust parser. No new TTL interpretation and no M3 bypass.
main_ttl=Path("crates/wbd-platform/src/rx_ipv4_tcp.rs").read_text()
android_io=Path("crates/wbd-platform/src/android_root_io.rs").read_text()
linux_io=Path("crates/wbd-platform/src/linux_raw_carrier.rs").read_text()
assert 'if packet[8] == 0 { return Err(RxError::WrongIpHeader); }' in main_ttl
assert 'if packet[8]==0{return Err(RxError::WrongIpHeader)}' in main_ttl
assert 'if packet[8] != trusted.persona.ttl()' not in main_ttl
assert 'if packet[8]!=trusted.persona.ttl()' not in main_ttl
assert 'fn h2216_original_windows_128_to_116_client_public_nat_data_and_ack()' in main_ttl
assert 'PacketPersona::Windows11, 116u8' in main_ttl
assert 'PacketPersona::Legacy, 52u8' in main_ttl
assert 'RxError::IpChecksum' in main_ttl
# A50 intentionally replaced the strict front gate with the M3-pending fast
# path; the original AEAD/PN verifier still decides actual delivery.
assert 'crate::rx_ipv4_tcp::parse_data_packet_android_m3_pending(' in android_io
# main Linux single kernel raw / multi-buffer receive both call the
# H2216 shared parser; n and len are distinct source-local variable names.
assert 'parse_data_packet_fast(&slot[..n],trusted)' in linux_io
assert 'parse_ack_packet(&slot[..n],trusted,false)' in linux_io
assert 'parse_data_packet_fast(&slot[..len],TrustedRx{' in linux_io
assert 'parse_ack_packet(&slot[..len],TrustedRx{' in linux_io
assert 'ANDROID_A46_MAIN_WINDOWS_H2216_ROUTED_TTL_DATA_ACK_RUST_HOST_PASS' in Path('android/root-native/ci/linux-original-oracle.sh').read_text()
# A47 actual same-socket RAW recv metadata, precise rejection buckets,
# seq/owner handoff outcomes; 4-second cumulative Go snapshots survive
# the Java APK file/report boundary via a strict numeric-only allowlist.
nativeio=Path("crates/wbd-platform/src/android_root_io.rs").read_text()
owner=Path("crates/wbd-engine/src/v4_owner_crypto.rs").read_text()
nativeworker=Path("crates/wbd-engine/src/v4_android_original_m4.rs").read_text()
gobridge=Path("r0/go_overlay/internal/realityfront/bridge_v4_embedded_android.go").read_text()
appwrite=Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java").read_text()
appreport=Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReport.java").read_text()
for name in ("RX_DATA_OK","RX_PURE_ACK","RX_TUPLE_BAD","RX_IP_CHECKSUM_BAD",
             "RX_TCP_CHECKSUM_BAD","RX_FLAGS_BAD","RX_LENGTH_BAD",
             "RX_OPTIONS_BAD","RX_SEQ_BAD","RX_OWNER_OFFER_BAD",
             "RX_LAST_SRC_IP","RX_LAST_DST_IP","RX_LAST_FLAGS"):
 assert name in nativeio,name
assert 'read_original_record(' in nativeio
assert 'parse_ack_packet(' in nativeio
assert 'driver.record_seq_reject()' in owner
assert 'driver.record_owner_offer_reject()' in owner
assert 'fn wbd_m0_embedded_go_loop_raw_rx_debug(' in nativeworker
assert 'C.wbd_m0_embedded_go_loop_raw_rx_debug(' in gobridge
assert 'wbd_m0_embedded_go_loop_raw_rx_debug' in Path("android/root-native/build-source-locked.sh").read_text()
assert 'originalAndroidM4RxSnapshot(' in go_product
assert 'originalAndroidM4OwnerSnapshot(' in go_product
assert 'TestA47OriginalNumericNativeM4Snapshots' in Path(
 "r0/go_overlay/internal/v4productcli/android_business_witness_linux_test.go").read_text()
assert 'ANDROID_A47_REAL_ORIGINAL_GO_NUMERIC_M4_SNAPSHOT_HOST_PASS' in Path("android/root-native/ci/linux-original-oracle.sh").read_text()
assert 'diagnostics.recordNativeSnapshot(line.substring(forensic))' in s
assert 'static boolean safeNativeSnapshot(String raw)' in appwrite
assert 'native_m4_numeric_debug_samples:' in appreport
assert 'ANDROID_A47_NATIVE_NUMERIC_M4_REAL_APK_REPORT_HOST_PASS' in Path(
 "android/root-app/ci/RootDiagnosticReportTest.java").read_text()
# A48: API36 source-locked physical handset actually returned 114
# original Rust RAW RX packets: 113 strict TCP checksum mismatches, zero
# tuple/IP/flags/length mismatches; normal M3 never saw them. Preserve
# strict Windows/Linux parser; ONLY Android Bionic may supply an untrusted
# candidate when every other original IPv4/TCP check has passed.
parser=Path("crates/wbd-platform/src/rx_ipv4_tcp.rs").read_text()
android_io=Path("crates/wbd-platform/src/android_root_io.rs").read_text()
linux_io=Path("crates/wbd-platform/src/linux_raw_carrier.rs").read_text()
owner=Path("crates/wbd-engine/src/v4_owner_crypto.rs").read_text()
# The main H222x DATA parser supersedes Android A50's separate parser
# implementation. Android forwards into the same public main fast parser.
assert 'pub fn parse_data_packet_fast' in parser
assert 'parse_data_packet_checked(packet, trusted, true)' in parser
assert 'parse_data_packet_checked(packet, trusted, false)' in parser
assert 'fn parse_data_packet_android_m3_pending' in parser
assert '#[cfg(any(target_os="android",test))]' in parser
assert 'parse_data_packet_fast(packet,trusted)' in parser
assert 'if strict {' in parser
assert 'sum = add_bytes(sum, tcp);' in parser
assert 'fast_data_is_minimal_outer_framing_until_m3_authentication' in parser
assert 'a48_android_m3_pending_accepts_only_tcp_checksum_drift_as_untrusted' in parser
assert 'let parsed=match crate::rx_ipv4_tcp::parse_data_packet_android_m3_pending(' in android_io
assert 'if (observed&127)==0' not in android_io
assert 'if cfg!(debug_assertions) && total>=40' in android_io
assert 'self.debug[RX_DATA_OK].fetch_add(1' in android_io
assert 'self.debug[RX_TCP_CHECKSUM_BAD].fetch_add(1' not in android_io
assert 'self.debug[RX_DATA_OK].fetch_add(1' in android_io
assert 'Err(crate::rx_ipv4_tcp::RxError::TcpChecksum)=>{' not in android_io
assert 'a49_single_pass_matches_a48_two_pass_android_admission' in parser
assert 'ProtectedCryptoError::AndroidWouldBlock' in nativeworker
assert 'Err(err) if err.kind()==std::io::ErrorKind::WouldBlock' in owner
assert 'if error.kind()!=io::ErrorKind::WouldBlock' in android_io
assert 'wait_readable(raw.readiness_fd(),0)' not in nativeworker
assert 'wait_readable(tun.readiness_fd(),0)' not in nativeworker
assert 'parse_data_packet_android_m3_pending' not in linux_io
assert 'parse_data_packet_fast(&slot[..n],trusted)' in linux_io
assert 'parse_data_packet_fast(&slot[..len],TrustedRx{' in linux_io
assert 'self.offer_after_active(slab,0..len,absolute,now)' in owner
assert 'ANDROID_A48_ANDROID_BIONIC_TCP_CHECKSUM_ONLY_M3_PENDING_HOST_PASS' in Path(
    "android/root-native/ci/linux-original-oracle.sh").read_text()
assert 'advertised_window:65_535' in nativeworker
assert 'advertised_window:65_535' in Path(
    'crates/wbd-engine/src/v4_embedded_go.rs').read_text()
# A52: main H2229 is the ONE original appearance ACK ledger on Android.
# Authenticated M3 changes the contiguous head, never M1's future high-water
# or a naked RAW ACK; the already-owned TX worker emits exact 40B ACKs at
# >=10ms only through the original PhysicalNetwork-bound RAW FD.
main_ack=Path("crates/wbd-engine/src/v4_presentation_ack.rs").read_text()
engine_entry=Path("crates/wbd-engine/src/v4_embedded_go.rs").read_text()
native_io=Path("crates/wbd-platform/src/android_root_io.rs").read_text()
rust_platform=Path("crates/wbd-platform/src/ipv4_tcp.rs").read_text()
oracle=Path("android/root-native/ci/linux-original-oracle.sh").read_text()
assert 'mod v4_presentation_ack;' in Path("crates/wbd-engine/src/lib.rs").read_text()
assert '#[cfg(any(feature="fec2_product_record",target_os="android"))]' in Path(
    "crates/wbd-engine/src/lib.rs").read_text()
assert 'a52_android_normal_off_ack_never_skips_authenticated_gap' in main_ack
assert 'android_presentation_ack:crate::v4_presentation_ack::NativePresentationAck' in engine_entry
assert 'android_presentation_ack:crate::v4_presentation_ack::NativePresentationAck::new(' in engine_entry
assert 'e.android_last_copied_seq32=tx_boundary' in engine_entry
assert 'let advanced=e.android_presentation_ack.verified(' in nativeworker
assert 'absolute.saturating_add(wire_len as u64)' in nativeworker
assert 'ack32:e.android_presentation_ack.ack()' in nativeworker
assert 'send_presentation_ack_if_due(' in nativeworker
assert 'presentation_ack_only_due(' in nativeworker
assert 'build_presentation_ack(' in nativeworker
assert 'raw.send_built_outer(e.generation,packet,scope.mtu)' in nativeworker
assert 'e.android_last_copied_seq32=seq_end' in nativeworker
assert 'record.metadata().seq.0' in owner
assert 'record.bytes().len()' in owner
assert 'driver.send_original_frozen(' in owner
assert 'pub fn signal_wake(&self)' in native_io
assert 'fn consume_wake(&self)' in native_io
assert native_io.count('self.consume_wake();')==2
assert 'pub fn send_built_outer(' in native_io
assert 'pub fn build_presentation_ack' in rust_platform
assert 'ANDROID_A52_MAIN_H2229_AUTH_CUMULATIVE_ACK_RUST_HOST_PASS' in oracle
# B3: the original-Go-authenticated lease and the ACTUAL one-reader
# Android M4 are connected to Rust's existing tunnel UDP53 inverse map.
# Do not mistake this for Android OS Resolver or CN8503 physical split.
root_ui=Path("android/root-app/src/org/wbdnext/rootclient/RootClientActivity.java").read_text()
root_svc=Path("android/root-app/src/org/wbdnext/rootclient/RootClientService.java").read_text()
argv=Path("android/root-app/src/org/wbdnext/rootclient/OriginalGoCommandArgs.java").read_text()
argv_test=Path("android/root-app/ci/OriginalGoCommandArgsTest.java").read_text()
nativecli=Path("r0/go_overlay/internal/v4productcli/linux.go").read_text()
client=Path("r0/go_overlay/internal/realityfront/bridge_v4_linux_client_product.go").read_text()
android_bridge=Path("r0/go_overlay/internal/realityfront/bridge_v4_embedded_android.go").read_text()
linux_bridge=Path("r0/go_overlay/internal/realityfront/bridge_v4_embedded_linux.go").read_text()
backend=Path("crates/wbd-engine/src/v4_android_dns_udp_flow.rs").read_text()
required=Path("android/root-native/build-source-locked.sh").read_text()
assert 'tunnelDNS.setChecked(true)' in root_ui
assert 'request.putExtra("tunnel_dns",tunnelDNS.isChecked())' in root_ui
assert 'intent.getBooleanExtra("tunnel_dns",false)' in root_svc
assert 'verifyTLS,tunnelDNS' in root_svc
assert 'if(tunnelDNS)args.add("--android-tunnel-dns")' in argv
assert 'absent(noDNS,"--android-tunnel-dns")' in argv_test
assert 'ANDROID_B3_TUNNEL_DNS_ON_OFF_REAL_GO_ARGV_HOST_PASS' in argv_test
assert 'androidTunnelDNS:=flags.Bool("android-tunnel-dns",false' in nativecli
assert 'c.androidTunnelDNS=*androidTunnelDNS' in nativecli
assert 'AndroidTunnelDNS:c.androidTunnelDNS' in nativecli
assert 'AndroidTunnelDNS bool' in client
assert 'bridge.enableAndroidTunnelDNS()' in client
assert 'v4ConfigureProductFec(bridge,mode,p.cfg.FECProfile,cold)' in client
assert 'V4_PUBLIC_ANDROID_TUNNEL_DNS_EFFECTIVE role=client enabled=1' in client
assert 'ORIGINAL_GO_POSTAUTH_TUNNEL_DNS_ENABLED' in root_svc
assert 'ORIGINAL_GO_POSTAUTH_TUNNEL_DNS_FAILED' in root_svc
assert 'ORIGINAL_GO_POSTAUTH_TUNNEL_DNS_ENABLED' in Path(
    "android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java").read_text()
assert 'ORIGINAL_GO_POSTAUTH_TUNNEL_DNS_FAILED' in Path(
    "android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReport.java").read_text()
assert 'ANDROID_B3B_COLD_NATIVE_DNS_EFFECTIVE_AND_FAILED_SAFE_REPORT_HOST_PASS' in Path(
    "android/root-app/ci/RootDiagnosticReportTest.java").read_text()
assert 'wbd_m0_embedded_go_android_tunnel_dns_enable' in android_bridge
assert 'wbd_m0_embedded_go_android_tunnel_dns_effective' in android_bridge
assert 'func (b *v4EmbeddedNativeBridge) enableAndroidTunnelDNS()error' in linux_bridge
assert 'pub extern "C" fn wbd_m0_embedded_go_android_tunnel_dns_enable(' in engine_entry
assert 'pub unsafe extern "C" fn wbd_m0_embedded_go_android_tunnel_dns_effective(' in engine_entry
assert 'e.android_dns_flows.stop();' in engine_entry
assert 'e.android_dns_hijack_ready=true;' in engine_entry
assert 'e.android_dns_physical_ready' in engine_entry
assert "DnsRoute::PhysicalUDP" in nativeworker
assert 'e.android_dns_flows.rewrite_query(' in nativeworker
# Rust formats the owner type and its method on separate source lines.
assert 'crate::v4_android_dns_udp_flow::TunnelDnsUdpFlows::' in owner
assert 'is_tunnel_reply_candidate(business)' in owner
assert 'dns_flows.rewrite_reply(' in owner
assert 'pub(crate) fn rewrite_query(' in backend
assert 'pub(crate) fn rewrite_reply(' in backend
assert 'wbd_m0_embedded_go_android_tunnel_dns_enable' in required
assert 'wbd_m0_embedded_go_android_tunnel_dns_effective' in required
assert 'hijack_enabled.write(0)' in nativeworker
# B3d original-M4 actual RAW-copy and M3 reverse-TUN counters.
original_owner=Path("crates/wbd-engine/src/v4_owner_crypto.rs").read_text()
assert 'dns_written=dns_written.saturating_add(1)' in original_owner
assert 'dns_tunnel_raw_copied.fetch_add(1' in nativeworker
assert 'dns_tunnel_reply_tun.fetch_add(u64::from(dns_written)' in nativeworker
assert 'dns_raw_copied.write(e.android_metrics.dns_tunnel_raw_copied' in nativeworker
assert 'dns_reply_tun.write(e.android_metrics.dns_tunnel_reply_tun' in nativeworker
assert 'DnsTunnelRawCopied:dnsRaw,DnsTunnelReplyTun:dnsTun' in android_bridge
assert 'DnsTunnelRawCopied,DnsTunnelReplyTun uint64' in linux_bridge
assert 'DNS_TUNNEL_RAW_COPIED' in nativecli
assert 'DNS_TUNNEL_REVERSE_TUN_WRITTEN' in nativecli
assert 'ORIGINAL_RUST_DNS_TUNNEL_REVERSE_TUN_WRITTEN' in root_svc
assert 'tunnel_dns_live=' in Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReport.java").read_text()
assert 'ANDROID_B3D_REAL_M4_DNS_QUERY_COPIED_AUTH_INVERSE_TUN_RECEIPT_HOST_PASS' in Path("android/root-app/ci/RootDiagnosticReportTest.java").read_text()

assert "dns_capture=NOT_CONNECTED" in nativecli
print("ANDROID_B3_REAL_ORIGINAL_M3_TUNNEL_UDP_DNS_COLD_WIRING_SOURCE_PASS")
print("ANDROID_B3D_REAL_M4_TUNNEL_DNS_TX_AND_AUTH_RX_WIRING_SOURCE_PASS")
# B4: explicit physical App UDP53 mode is a distinct production path.
assert 'physicalDNS.setChecked(false)' in root_ui
assert 'request.putExtra("physical_dns",physicalDNS.isChecked())' in root_ui
assert 'physicalDNS.setOnCheckedChangeListener' in root_ui
assert 'intent.getBooleanExtra("physical_dns",false)' in root_svc
assert 'verifyTLS,tunnelDNS,physicalDNS' in root_svc
assert 'if(physicalDNS)args.add("--android-physical-dns")' in argv
assert 'ANDROID_B4_REAL_PHYSICAL_DNS_SELECTED_ALL_APP_GO_ARGV_HOST_PASS' in argv_test
assert 'androidPhysicalDNS:=flags.Bool("android-physical-dns",false' in nativecli
assert 'c.androidPhysicalDNS=*androidPhysicalDNS' in nativecli
assert 'AndroidPhysicalDNS:c.androidPhysicalDNS' in nativecli
assert 'AndroidPhysicalDNS bool' in client
assert 'bridge.enableAndroidPhysicalDNS()' in client
assert 'V4_PUBLIC_ANDROID_PHYSICAL_DNS_EFFECTIVE role=client cold=1' in client
assert 'wbd_m0_embedded_go_android_physical_dns_enable' in android_bridge
assert 'wbd_m0_embedded_go_android_physical_dns_effective' in android_bridge
assert 'func (b *v4EmbeddedNativeBridge) enableAndroidPhysicalDNS()error' in linux_bridge
assert 'wbd_m0_embedded_go_android_physical_dns_enable' in required
assert 'wbd_m0_embedded_go_android_physical_dns_effective' in required
assert 'pub extern "C" fn wbd_m0_embedded_go_android_physical_dns_enable(' in engine_entry
assert 'e.android_dns_physical_ready=true;' in engine_entry
assert 'AndroidBoundPhysicalDnsUdp::open(' in nativeworker
assert 'dns_physical_tx.fetch_add(1' in nativeworker
assert 'dns_physical_rx.fetch_add(1' in nativeworker
assert 'physical_tx.write(e.android_metrics.dns_physical_tx' in nativeworker
assert 'physical_rx.write(e.android_metrics.dns_physical_rx' in nativeworker
assert 'DnsPhysicalTx:physTx,DnsPhysicalRx:physRx,DnsPhysicalError:physErr' in android_bridge
assert 'DNS_PHYSICAL_REVERSE_TUN_WRITTEN' in nativecli
assert 'ORIGINAL_RUST_DNS_PHYSICAL_REVERSE_TUN_WRITTEN' in root_svc
assert 'physical_dns_live=' in Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReport.java").read_text()
assert 'ANDROID_B4_PHYSICAL_DNS_COLD_REAL_SOCKET_TX_RX_REPORT_HOST_PASS' in Path("android/root-app/ci/RootDiagnosticReportTest.java").read_text()
print("ANDROID_B4_REAL_PHYSICAL_APP_UDP53_RUST_GO_JAVA_COLD_AND_LIVE_WIRING_SOURCE_PASS")

# B5 actual CN8503 split: complete App UI -> Go cold -> Rust M4 worker.
root_receipt=Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReceipt.java").read_text()
cn_rule=Path("crates/wbd-engine/src/v4_android_cn_dns.rs").read_text()
go_cn=Path("r0/go_overlay/internal/v4productcli/dnsnative/cn_rules.go").read_text()
assert 'cnSplitDNS.setChecked(false)' in root_ui
assert 'request.putExtra("cn_dns_split",cnSplitDNS.isChecked())' in root_ui
assert 'intent.getBooleanExtra("cn_dns_split",false)' in root_svc
assert 'managerPackages,bypassPackages,bypassUIDs,' in root_svc
assert 'verifyTLS,tunnelDNS,physicalDNS,cnSplitDNS,requestedOuterMTU,recordCipher,requestedTunQueue,paddingMode,fecMode,fecProfile,directCIDRs,physicalDnsIPv4,nativeHealthSeconds);' in root_svc
assert 'if(cnSplitDNS)args.add("--android-cn-dns-split")' in argv
assert 'ANDROID_B5_CN8503_SPLIT_SELECTED_ALL_APP_AND_LEGACY_GO_ARGV_HOST_PASS' in argv_test
assert 'androidCNDNSSplit:=flags.Bool("android-cn-dns-split",false' in nativecli
assert 'c.androidCNDNSSplit=*androidCNDNSSplit' in nativecli
assert 'AndroidCN8503Raw:cn8503Raw' in nativecli
assert 'AndroidCN8503Raw []byte' in client
assert 'bridge.enableAndroidCNDNSSplit(p.cfg.AndroidCN8503Raw)' in client
assert 'func (b *v4EmbeddedNativeBridge) enableAndroidCNDNSSplit(raw []byte)error' in android_bridge
assert 'func (b *v4EmbeddedNativeBridge) enableAndroidCNDNSSplit(_ []byte)error' in linux_bridge
assert 'wbd_m0_embedded_go_android_cn_dns_split_enable' in required
assert 'wbd_m0_embedded_go_android_cn_dns_split_effective' in required
assert 'pub unsafe extern "C" fn wbd_m0_embedded_go_android_cn_dns_split_enable(' in engine_entry
assert 'e.android_cn_dns=Some(Arc::new(matcher));' in engine_entry
assert 'e.android_cn_dns=None;' in engine_entry
assert 'crate::v4_android_dns_route::choose(' in nativeworker
assert nativeworker.count('crate::v4_android_dns_route::choose(')==2
assert 'android_cn_dns.is_some()' in nativeworker
assert 'RegexSetBuilder::new(patterns)' in cn_rule
assert 'pub(crate) fn is_cn_ipv4_query' in cn_rule
assert 'r.raw=append([]byte(nil),raw...)' in go_cn
assert 'ORIGINAL_GO_POSTAUTH_CN_DNS_SPLIT_ENABLED' in root_svc
assert 'ORIGINAL_GO_POSTAUTH_CN_DNS_SPLIT_ENABLED' in root_receipt
assert 'cn_dns_split_live=' in Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReport.java").read_text()
assert 'ANDROID_B5_CN8503_SPLIT_COLD_AND_DUAL_PATH_REPORT_HOST_PASS' in Path("android/root-app/ci/RootDiagnosticReportTest.java").read_text()
assert 'cargo +1.85.1 test --locked -p wbd-engine --lib b5_cn8503' in Path("android/root-native/ci/dns-b2-pinned-cn.sh").read_text()
print("ANDROID_B5_REAL_CN8503_ORIGINAL_M4_DUAL_DNS_APP_GO_RUST_SOURCE_PASS")
# B6 same real original M4: full packet route, TCP53 unchanged encrypted
# tunnel, physical TC reply actually inserted, four new readonly counters.
router=Path("crates/wbd-engine/src/v4_android_dns_route.rs").read_text()
assert 'mod v4_android_dns_route;' in Path("crates/wbd-engine/src/lib.rs").read_text()
assert 'DnsRoute::TCP53OriginalTunnel' in nativeworker
assert 'tcp53_original:matches!(route' in nativeworker
assert 'stats.dns_tcp53_original_raw.fetch_add(1' in nativeworker
assert 'stats.dns_noncn_tunnel_raw.fetch_add(1' in nativeworker
assert 'stats.dns_cn_physical_sent.fetch_add(1' in nativeworker
assert 'stats.dns_physical_tc_tun.fetch_add(1' in nativeworker
assert 'physical_packet[30]&0x02!=0' in nativeworker
assert 'pub unsafe extern "C" fn wbd_m0_embedded_go_loop_dns_route_receipts(' in nativeworker
assert 'wbd_m0_embedded_go_loop_dns_route_receipts' in required
assert 'wbd_m0_embedded_go_loop_dns_route_receipts' in android_bridge
assert 'originalAndroidDNSRouteReceipts()' in android_bridge
assert 'DnsCNPhysicalSent:route[0]' in android_bridge
assert 'DnsCNPhysicalSent,DnsNonCNTunnelRaw,DnsTCP53OriginalRaw,DnsPhysicalTCTun' in linux_bridge
assert 'originalAndroidDNSB6Snapshot(p realityfront.V4PublicLoopPulse)' in nativecli
assert 'DNS_CN_PHYSICAL_SENT' in nativecli
assert 'DNS_NONCN_TUNNEL_RAW_COPIED' in nativecli
assert 'DNS_TCP53_ORIGINAL_RAW_COPIED' in nativecli
assert 'DNS_PHYSICAL_TC_REPLY_TUN_WRITTEN' in nativecli
assert 'ORIGINAL_RUST_DNS_CN_PHYSICAL_SENT' in root_svc
assert 'ORIGINAL_RUST_DNS_NONCN_TUNNEL_RAW_COPIED' in root_svc
assert 'ORIGINAL_RUST_DNS_TCP53_ORIGINAL_RAW_COPIED' in root_svc
assert 'ORIGINAL_RUST_DNS_PHYSICAL_TC_REPLY_TUN_WRITTEN' in root_svc
assert 'recordDNSB6Snapshot(line.substring(dnsB6))' in root_svc
assert 'safeDNSB6Snapshot(String raw)' in root_receipt
assert 'cn_dns_split_route_copies=' in Path("android/root-app/src/org/wbdnext/rootclient/RootDiagnosticReport.java").read_text()
assert 'ANDROID_B6_REAL_CN_NONCN_TCP53_TC_ROUTE_RECEIPT_HOST_PASS' in Path("android/root-app/ci/RootDiagnosticReportTest.java").read_text()
assert 'b6_original_m4_cn_physical_tc_inverse_and_noncn_tunnel_inverse' in router
assert 'b6_original_m4_dns_three_compat_modes_and_tcp53_passthrough' in router
assert 'cargo +1.85.1 test --locked -p wbd-engine --lib b6_original_m4' in Path("android/root-native/ci/dns-b2c2b-rust-udp-map-host.sh").read_text()
assert nativeworker.count("tun.read_ip_scatter(")==1
print("ANDROID_B6_ORIGINAL_M4_DNS_CN_NONCN_TCP53_TC_M4_ABI_AND_APP_REPORT_SOURCE_PASS")
# B7 real original M4 physical DNS retransmit and operator-only receipt.
physical_flow=Path("crates/wbd-engine/src/v4_android_dns_physical_flow.rs").read_text()
device_accept=Path("android/root-app/ci/device_first_run.py").read_text()
assert 'let identical=self.entries.iter().position(' in physical_flow
assert 'Ok((dns.len(),synthetic,new_slot))' in physical_flow
assert nativeworker.count('if new_slot{physical_flows.cancel(id);}')==2
assert 'b7_physical_dns_app_retransmit_reuses_generation_slot_not_other_apps' in physical_flow
assert 'b7_physical_dns_retransmit_expiry_and_query_identity' in physical_flow
assert 'cargo +1.85.1 test --locked -p wbd-engine --lib b7_physical_dns' in Path("android/root-native/ci/dns-b2c2b-rust-udp-map-host.sh").read_text()
assert 'cn8503_m4_dual_dns_query_and_reply_observed' in device_accept
assert 'android_system_netd_dns_interception": "NOT_RUN"' in device_accept
assert 'real_app_dns_answer_bytes_and_latency": "NOT_RUN"' in device_accept
print("ANDROID_B7_LOSSY_PHYSICAL_DNS_RETRANSMIT_AND_OPERATOR_RECEIPT_SOURCE_PASS")
assert 'RootDNSStatusBrief.fromReport(report)' in root_ui
assert 'dnsStatusBrief.setText(' in root_ui
assert '查看本会话DNS收发' in root_ui
brief=Path("android/root-app/src/org/wbdnext/rootclient/RootDNSStatusBrief.java").read_text()
assert 'system_netd_dns_capture' in brief
assert '不代表浏览器DNS' in brief
assert 'ANDROID_B7_APP_LOCAL_DNS_LIVE_REPORT_CURRENT_SESSION_HOST_PASS' in Path("android/root-app/ci/RootDiagnosticReportTest.java").read_text()
print("ANDROID_B7_APP_READONLY_DNS_SESSION_DIAGNOSTIC_BUTTON_SOURCE_PASS")

print("ANDROID_A52_MAIN_H2229_REAL_BIONIC_ACK_ONLY_SOURCE_GATE_PASS")
print("ANDROID_A51_MAIN_WINDOW65535_ANDROID_M4_PARITY_SOURCE_PASS")
print("ANDROID_A51_MAIN_FAST_DATA_SHARED_WITH_ANDROID_M3_SOURCE_PASS")
print("ANDROID_A49_SINGLE_PASS_AND_BOUNDED_NONBLOCKING_DRAIN_SOURCE_PASS")
print("ANDROID_A48_EXACT_ANDROID_ONLY_CHECKSUM_GATE_M3_AUTH_STILL_REQUIRED_SOURCE_PASS")
print("ANDROID_A47_ORIGINAL_RUST_RAW_NUMERIC_AND_GO_JAVA_FORENSICS_SOURCE_PASS")
print("ANDROID_A46_EXACT_MAIN_WINDOWS_H2216_TTL_ANDROID_LINUX_SOURCE_GATE_PASS")
print("ANDROID_A45_ORIGINAL_M4_RETURN_PATH_ICMP_SOURCE_GATE_PASS")
print("ANDROID_A44_ORIGINAL_M4_APP_BUSINESS_AND_UID_ROUTE_GET_SOURCE_PASS")
print("ANDROID_A43_ORIGINAL_GO_CLIENT_RX_QUIESCE_SOURCE_GATE_PASS")
print("ANDROID_A42_ORIGINAL_M4_POST_START_HANDOFF_SOURCE_GATE_PASS")
print("ANDROID_A41_ANDROID_TUN_LEASE32_NATIVE_GETIFADDRS_SOURCE_PASS")
print("ANDROID_A40_ORIGINAL_GO_RUST_POSTAUTH_STAGE_HOST_SOURCE_PASS")
print("ANDROID_A39_ANDROID_KEYSTORE_PROVIDER_IV_AND_START_NONBLOCKING_SOURCE_PASS")
print("ANDROID_A38_KEYSTORE_ENCRYPTED_SECRET_AUTOFILL_SOURCE_GATE_PASS")
assert 'v4AndroidCertFailureReason(err)' in go_admission
for e in ("ROOT_RESTORE_COMPLETE","ROOT_RESTORE_FAILED"):
 assert e in s and e in receipt and e in report
# Certificate subtypes need to be recognized in the native stdout parser
# and the fixed Event enum. The existing report emits validated events
# generically; it correctly does NOT hardcode every certificate subtype.
assert "ORIGINAL_GO_TLS_CERT_REASON_HOSTNAME_MISMATCH" in s
assert "ORIGINAL_GO_TLS_CERT_REASON_HOSTNAME_MISMATCH" in receipt
assert "RootDiagnosticReceipt.safeEventToken(event)" in report
print("ANDROID_A36_APP_RESTORE_CERT_TRUST_SOURCE_GATE_PASS")
print("ANDROID_NETWORK_EVENT_NO_POLLING_SOURCE_GATE_PASS")
PY

# B58 original Android selected-App / full ordinary-App route expansion.
# All three production modes retain one Go owner, original kernel ip rules,
# the same durable journal/Stop and final exact kernel table readback.
python3 - <<'PY'
from pathlib import Path
java=Path("android/root-app/src/org/wbdnext/rootclient")
go=Path("r0/go_overlay/internal/v4productcli")
group=(go/"rootjournal/group.go").read_text()
allapps=(go/"rootjournal/allapps.go").read_text()
single=(go/"rootjournal/journal.go").read_text()
direct=(go/"rootjournal/direct.go").read_text()
cli=(go/"linux.go").read_text()
selected=(java/"SelectedAppGroup.java").read_text()
routes=(java/"RootDirectIPv4.java").read_text()
argv=(java/"OriginalGoCommandArgs.java").read_text()
app=(java/"RootClientActivity.java").read_text()
assert 'static final int MAX_UIDS=16;' in selected
assert 'static final int MAX_PACKAGES=32;' in selected
assert 'targetUids.length>16' in argv
assert 'static final int MAX_PREFIXES=16;' in routes
assert 'const GroupMaxUIDs = 16' in group
assert 'const MaxDirectIPv4CIDRs=16' in direct
assert 'if len(parts)<2||len(parts)>16{' in cli
assert '2..16 ordinary App UIDs' in cli
assert '最多16个不同UID、32个包' in app
assert '最多16个IPv4直连网段' in routes
# Keep the final full-table readback; avoid quadratic re-queries inside UID
# loops and keep one aggregate direct FIB gate BEFORE the first UID add.
assert 'allDirectPresent(direct)||anyRules(rules)' in allapps
assert 'allDirectPresent(direct)||anyRules(rules)' in group
assert 'allDirectPresent(direct)||rule' in single
assert 'if e=s.requireReady(original);e!=nil{' in allapps
assert 'if err=s.requireReady(original);err!=nil{' in group
assert 'if err=s.requireReady(original);err!=nil{' in single
assert 's.query(original)' not in allapps.split('for i,r:=range original.ranges(){',1)[1].split('if e=s.requireReady(original);e!=nil',1)[0]
assert 's.query(original)' not in group.split('for i,uid:=range original.UIDs {',1)[1].split('if err=s.requireReady(original);err!=nil',1)[0]
assert 'TestB58SixteenRealSelectedUIDsBoundedKernelReadbacks' in (go/"rootjournal/group_test.go").read_text()
assert 'TestB58AllAppsConstantReadbackAcrossAllTwentyUserProfiles' in (go/"rootjournal/allapps_test.go").read_text()
assert 'TestB58SixteenDirectPrefixesAndSixteenAppUIDsOriginalKernel' in (go/"rootjournal/direct_integration_test.go").read_text()
assert 'TestB58OriginalGoColdSixteenSelectedUIDs' in (go/"android_parse_reason_linux_test.go").read_text()
print("ANDROID_B58_SELECTED_16_UID_32_PACKAGES_AND_DIRECT_16_CIDRS_ORIGINAL_ROOT_SOURCE_PASS")
print("ANDROID_B58_SINGLE_GROUP_ALL_APP_CONSTANT_KERNEL_READBACK_SOURCE_PASS")
PY

# B59: original Normal/Game physically scoped DNS jumbo reply to one TUN.
python3 - <<'PY'
from pathlib import Path
eng=Path("crates/wbd-engine/src")
normal=(eng/"v4_android_original_m4.rs").read_text()
game=(eng/"v4_android_game_m4.rs").read_text()
dns=(eng/"v4_android_dns_physical_flow.rs").read_text()
io=Path("crates/wbd-platform/src/android_root_io.rs").read_text()
for owner in (normal,game):
 assert owner.count("emit_physical_dns_tun_reply(")==1
 assert owner.count("write_scoped_physical_dns_ipv4_fragment(")==1
 assert owner.count("write_scoped_physical_dns_ip(")>=1
assert normal.count("tun.read_ip_scatter(")==1
assert game.count("tx_tun.read_ip(")==1
assert 'pub(crate) fn emit_physical_dns_tun_reply(' in dns
assert 'crate::v4_android_ipv4_mtu::fragment(' in dns
assert 'pub fn write_scoped_physical_dns_ipv4_fragment(' in io
print("ANDROID_B59_NORMAL_GAME_PHYSICAL_EDNS_ORIGINAL_TUN_RFC791_SOURCE_PASS")
PY

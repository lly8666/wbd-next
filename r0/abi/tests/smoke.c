#include <stdio.h>
#include <string.h>
#include "wbd_abi.h"

#define CHECK(expr) do {if (!(expr)) { fprintf(stderr,"C ABI assertion line %d: %s\n",__LINE__,#expr);return 1; }} while (0)

int main(void) {
    WbdAbiInfoV1 info={.abi_version=99,.struct_size=99,.features=~0ull,.reserved=~0ull};
    CHECK(wbd_r0_abi_query(NULL, 24)==WBD_R0_NULL_ARG);
    CHECK(wbd_r0_abi_query(&info,23)==WBD_R0_BAD_SIZE);
    CHECK(info.abi_version==99 && info.features==~0ull);
    CHECK(wbd_r0_abi_query(&info,24)==WBD_R0_OK);
    CHECK(info.abi_version==WBD_R0_ABI_VERSION && info.struct_size==24 &&
          info.features==0 && info.reserved==0);
    WbdAbiConfigV1 cfg={.abi_version=1,.struct_size=16,.flags=0,.reserved=0};
    WbdEngineToken untouched={.value=0x55};
    CHECK(wbd_r0_engine_open(NULL,16,&untouched)==WBD_R0_NULL_ARG);
    CHECK(wbd_r0_engine_open(&cfg,16,NULL)==WBD_R0_NULL_ARG);
    cfg.struct_size=12;
    CHECK(wbd_r0_engine_open(&cfg,16,&untouched)==WBD_R0_BAD_SIZE && untouched.value==0x55);
    cfg.struct_size=24;
    CHECK(wbd_r0_engine_open(&cfg,16,&untouched)==WBD_R0_BAD_SIZE && untouched.value==0x55);
    cfg.struct_size=16;
    CHECK(wbd_r0_engine_open(&cfg,12,&untouched)==WBD_R0_BAD_SIZE && untouched.value==0x55);
    cfg.abi_version=2;
    CHECK(wbd_r0_engine_open(&cfg,16,&untouched)==WBD_R0_BAD_VERSION && untouched.value==0x55);
    cfg.abi_version=1; cfg.flags=1;
    CHECK(wbd_r0_engine_open(&cfg,16,&untouched)==WBD_R0_UNSUPPORTED && untouched.value==0x55);
    cfg.flags=0; cfg.reserved=1;
    CHECK(wbd_r0_engine_open(&cfg,16,&untouched)==WBD_R0_UNSUPPORTED && untouched.value==0x55);
    cfg.reserved=0;
    WbdEngineToken e={0}, newer={0};
    WbdLaneToken lane={0}, replacement={0}, wrongkind={0};
    CHECK(wbd_r0_engine_open(&cfg,16,&e)==WBD_R0_OK && e.value!=0);
    CHECK(wbd_r0_lane_open(e,NULL)==WBD_R0_NULL_ARG);
    CHECK(wbd_r0_lane_open(e,&lane)==WBD_R0_OK && lane.value!=0);
    wrongkind.value=e.value;
    CHECK(wbd_r0_lane_close(wrongkind)==WBD_R0_STALE);
    CHECK(wbd_r0_engine_close((WbdEngineToken){lane.value})==WBD_R0_STALE);
    CHECK(wbd_r0_lane_close(lane)==WBD_R0_OK);
    CHECK(wbd_r0_lane_close(lane)==WBD_R0_STALE);
    CHECK(wbd_r0_lane_open(e,&replacement)==WBD_R0_OK && replacement.value!=lane.value);
    CHECK(wbd_r0_engine_close(e)==WBD_R0_OK);
    CHECK(wbd_r0_lane_close(replacement)==WBD_R0_STALE);
    CHECK(wbd_r0_lane_open(e,&lane)==WBD_R0_STALE);
    CHECK(wbd_r0_engine_close(e)==WBD_R0_STALE);
    CHECK(wbd_r0_engine_open(&cfg,16,&newer)==WBD_R0_OK && newer.value!=e.value);
    CHECK(wbd_r0_lane_open(newer,&lane)==WBD_R0_OK);
    CHECK(wbd_r0_lane_close(lane)==WBD_R0_OK);
    CHECK(wbd_r0_engine_close(newer)==WBD_R0_OK);
    puts("R0_NATIVE_C_ABI_PASS version=1 info=24 config=16 features=0 stale/generation/errors/close");
    return 0;
}

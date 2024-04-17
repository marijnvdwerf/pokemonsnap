#include "common.h"
#include "os_cache.h"
#include "sys/dma.h"

#if 1
#define segmentRomStart(name) name##_ROM_START 
#define segmentRomEnd(name) name##_ROM_END
#define segmentStart(name) name##_VRAM 

#define SEGMENT(name) extern char segmentRomStart(name)[], segmentRomEnd(name)[], segmentStart(name)[];

#define loadSegment(name)   dma_rom_read((uintptr_t)&segmentRomStart(name),&segmentStart(name),segmentRomEnd(name) - segmentRomStart(name));


#define stage0 D_800ABE10
#define stage1 D_800ABE58
#define stage4 D_800ABEA0
#define stage3 D_800ABEE8
#define stage2 D_800ABF30
#define stage5 D_800ABF78
#define stage6 D_800ABFC0

SEGMENT(magikarp1) //     731b0
SEGMENT(pikachu1) //      7d3b0
SEGMENT(zubat1) //        98470
SEGMENT(bulbasaur1) //    99f70
SEGMENT(stage0_extra) // 13c780
SEGMENT(stage1_extra) // 1d1d90
SEGMENT(stage4_extra) // 27ab80
SEGMENT(stage3_extra) // 30af90
SEGMENT(stage2_extra) // 3d0560
SEGMENT(stage5_extra) // 47cf30
SEGMENT(stage6_extra) // 4ec000
SEGMENT(magikarp2) //    82f8e0
SEGMENT(pikachu2) //     832960
SEGMENT(zubat2) //       837360
SEGMENT(bulbasaur2) //   83a1e0


// Could be an array
extern Overlay stages[7]; // 0x800abe10

extern Overlay stage0; // 0x800abe10
extern Overlay stage1; // PTR_DAT_800abe58
extern Overlay stage2; // 0x800abf30
extern Overlay stage3; // 0x800abee8
extern Overlay stage4; // PTR_DAT_800abea0
extern Overlay stage5; // 0x800abf78
extern Overlay stage6; // 0x800abfc0
#endif

extern Overlay D_800ABBD0;
extern Overlay D_800ABDEC;
extern s32 D_800AC00C;
extern s32 D_800B0578;

void func_8009A8C0(s32 arg0) {
    D_800B0578 = arg0;
}

s32 func_8009A8CC(void) {
    return D_800B0578;
}

void func_8009A8D8(s32 arg0) {
    D_800AC00C = arg0;
}

s32 func_8009A8E4(void) {
    return D_800AC00C;
}


void func_8009A8F0(int param_1)
{
  switch(param_1) {
  case 0:
    load_overlay(&stage0);
    loadSegment(stage0_extra);
    loadSegment(magikarp1);
    loadSegment(magikarp2);
    loadSegment(pikachu1);
    loadSegment(pikachu2);
    break;
  case 1:
    load_overlay(&stage1);
    loadSegment(stage1_extra);
    loadSegment(magikarp1);
    loadSegment(magikarp2);
    loadSegment(pikachu1);
    loadSegment(pikachu2);
    loadSegment(zubat1);
    loadSegment(zubat2);
    break;
  case 4:
    load_overlay(&stage4);
    loadSegment(stage4_extra);
    loadSegment(bulbasaur1);
    loadSegment(bulbasaur2);
    loadSegment(magikarp1);
    loadSegment(magikarp2);
    loadSegment(pikachu1);
    loadSegment(pikachu2);
    loadSegment(zubat1);
    loadSegment(zubat2);
    break;
  case 3:
    load_overlay(&stage3);
    loadSegment(stage3_extra);
    loadSegment(bulbasaur1);
    loadSegment(bulbasaur2);
    loadSegment(magikarp1);
    loadSegment(magikarp2);
    loadSegment(pikachu1);
    loadSegment(pikachu2);
    break;
  case 2:
    load_overlay(&stage2);
    loadSegment(stage2_extra);
    loadSegment(magikarp1);
    loadSegment(magikarp2);
    break;
  case 5:
    load_overlay(&stage5);
    loadSegment(stage5_extra);
    loadSegment(magikarp1);
    loadSegment(magikarp2);
    break;
  case 6:
    load_overlay(&stage6);
    loadSegment(stage6_extra);
  }
  return;
}

#pragma GLOBAL_ASM("asm/nonmatchings/46270/func_8009AE0C.s")

#pragma GLOBAL_ASM("asm/nonmatchings/46270/func_8009B2BC.s")

void func_8009B40C(void) {
    s32 i = 0;

    for (i = 0;;) {
        load_overlay(&D_800ABDEC);
        load_overlay(&D_800ABBD0);
        if (func_801DD010(i) != 0) {
            while (TRUE);
        }
        i++;
        if (i == 0x11) {
            while (TRUE);
        }
    }
}

#pragma GLOBAL_ASM("asm/nonmatchings/46270/start_scene_manager.s")

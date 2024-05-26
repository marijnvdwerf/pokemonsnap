#include "common.h"
#include "world/world.h"

void func_802DB0B8_72C2B8(GObj*);

extern PokemonInitData D_802E2710_733910;

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DAAE0_72BCE0.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DAB90_72BD90.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DAC38_72BE38.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DACA8_72BEA8.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DAD4C_72BF4C.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DADA8_72BFA8.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DAE4C_72C04C.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DAEA8_72C0A8.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DAF18_72C118.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DAF88_72C188.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DAFF8_72C1F8.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DB06C_72C26C.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DB0B8_72C2B8.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DB140_72C340.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DB1C4_72C3C4.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DB274_72C474.s")

void func_802DB2D4_72C4D4(GObj* arg0) {
    updatePokemonState(arg0, func_802DB0B8_72C2B8);
}

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DB2F8_72C4F8.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DB358_72C558.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DB3CC_72C5CC.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DB418_72C618.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DB48C_72C68C.s")

#pragma GLOBAL_ASM("asm/nonmatchings/volcano/72BCE0/func_802DB4E8_72C6E8.s")

GObj* func_802DB558_72C758(s32 objID, u16 id, WorldBlock* block, WorldBlock* blockB, ObjectSpawn* spawn, PokemonInitData* initData) {
    return spawnPokemonOnGround(objID, id, block, blockB, spawn, &D_802E2710_733910);
}

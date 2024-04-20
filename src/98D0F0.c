#include "common.h"

#include "gbi.h"
#include "string.h"
#include "sys/vi.h"
#include "sys/cont.h"


s32 D_801F3E60_9A38D0 = 0;

//??
char* D_801F3E64_9A38D4[] = {
    0,
    0,
    0,
    0,
    "Surfing PIKACHU",
    "PIKACHU on a Ball",
    "Balloon PIKACHU",
    "Speed PIKACHU",
    "PIKACHU on a Stump",
    "Flying PIKACHU",
    "Gust-using PIDGEY",
    "JIGGLYPUFF on Stage",
    "GRAVELER's Group Dance",
    "The Rare Pokεmon MEW",
    "Fighting MAGMAR",
    "JIGGLYPUFF TRIO on Stage",
    "wrong number!",
    "\\BOh! It seems to be screeching.",
    "\\BOh! This is a fighting pose.",
    "\\BOh! It's happy.",
    "This is a relaxed pose.",
    "\\BOh! It's neighing.",
    "\\BOh! So many embers!",
    "\\BOh! Tons of embers!",
    "\\BOh! It's shining.",
    "\\BOh! It's shining.",
    "\\BOh! It's about to leap out!",
    "\\BOh! It's enjoying the food.",
    "\\BOh! It's DRAGONITE!",
    "\\BOh! What a Thunder Jolt!",
    "\\BOh! It's happy.",
    "It looks happy.",
    "\\BOh! It's happy.",
    "\\BOh! What a jolly dance!",
    "\\BOh! How beautiful!",
    "\\BOh! How powerful!",
    "It just showed its face.",
    "Umm... looks scary!",
    "\\BOh! It's furious!",
    "\\BOh! It looks astonished!",
    "JIGGLYPUFF's dance is great!",
    "\\BOh! That's a shame...",
    "\\BOh! It's singing cheerfully.",
    "It's rolling...",
    "\\BOh! It exploded!",
    "It's a blast!",
    "Oh dear, it fainted.",
    "You've thrown a PESTER BALL.",
    "It must be angry.",
    "\\BOh! It's surprised!",
    "It sure is happy!",
    "It's trying to go underground.",
    "I can barely see it.",
    "It's trying to go underground.",
    "\\BOh! What an amazing jump!",
    "That's a pretty good jump.",
    "It's jumping.",
    "\\BOh! It's falling.",
    "\\BOh! It's falling.",
    "\\BOh! It fell.",
    "\\BOh! It's MANKEY in the sky!",
    "\\BOh! MANKEY got blasted!",
    "You've thrown a PESTER BALL.",
    "You've thrown a PESTER BALL.",
    "\\BOh! What a splash!",
    "It splashed!",
    "That's a good splash.",
    "\\BOh! It's splashing.",
    "Nice jump.",
    "It's jumping.",
    "\\BOh! What a jump!",
    "It's dizzy.",
    "Oh dear, it fainted.",
    "\\BOh! It's about to wake up.",
    "\\BOh! It's about to jump in!",
    "You've thrown a PESTER BALL.",
    "You've thrown a PESTER BALL.",
    "You've thrown a PESTER BALL.",
    "\\BOh! It's about to pop up.",
    "It's about to go underground.",
    "Hmm... It looks jolly.",
    "It stumbled.",
    "It stumbled.",
    "It stumbled.",
    "\\BOh! It's about to pop up.",
    "It's about to go underground.",
    "\\BOh! It's happy.",
    "That's a good splash!",
    "It's splashing.",
    "\\BOh! What a splash!",
    "You've thrown a PESTER BALL.",
    "You've thrown a PESTER BALL.",
    "You've thrown a PESTER BALL.",
    "It's about to withdraw.",
    "I only see its shell.",
    "It's about to come out.",
    "\\BOh! It's happy!",
    "Hmm... It looks happy.",
    "Hmm... It looks jolly.",
    "\\BOh! It sure is jolly!",
    "Isn't the Pokεmon dance fun?",
    "\\BOh! It's rockin'!",
    "\\BOh! It's about to wake up!",
    "\\BOh! It's been caught!",
    "\\BOh! It's snapping!",
    "It looks like it's going to fish.",
    "Nice jump.",
    "It jumped.",
    "\\BOh! What a jump!",
    "It's about to fall.",
    "Quite unique!",
    "It's submerging.",
    "You've thrown a PESTER BALL.",
    "You've thrown a PESTER BALL.",
    "You've thrown a PESTER BALL.",
    "\\BOh! What a happy face!",
    "\\BOh! What a wonderful pose!",
    "It looks like it's shocked.",
    "\\BOh! What a flame!",
    "It's unstable...",
    "Hmm...",
    "You've thrown a PESTER BALL.",
    "\\BOh! It looks happy!",
    "Interesting! It's dizzy!",
    "It's unstable...",
    "This is pretty funny!",
    "Ha, ha, ha! This is so funny!",
    "\\BOh! It looks hot!",
    "It's about to fall.",
    "It seems to have fainted.",
    "It seems to have woken up.",
    "\\BOh! It's roaring!",
    "You've thrown a PESTER BALL.",
    "You've thrown a PESTER BALL.",
    "You've thrown a PESTER BALL.",
    "Hmm... It looks happy.",
    "wrong number!",
    "wrong number!",
    "\\BOh! It looks jolly.",
    "\\BOh! You hit 'em!",
    "\\BOh! It just fainted.",
    "\\BOh! It's about to wake up.",
    "This angry shot is pretty cool.",
    "\\BOh! What an interesting pose!",
    "It's pretty funny.",
    "It seems to have fainted.",
    "You've thrown a PESTER BALL.",
    "\\BOh! A dancing MEOWTH!",
    "That's SNORLAX for sure!",
    "\\BOh! What a jolly dance!",
    "This pose zaps even me!",
    "\\BOh! This is very lively!",
    "wrong number!",
    "wrong number!",
    "wrong number!",
    "wrong number!",
    "wrong number!",
    "wrong number!",
    "wrong number!",
    "wrong number!",
    "wrong number!",
    "\\BOh! That's PIKA!",
    "wrong number!",
    "wrong number!",
    "wrong number!",
    "If only it were facing you...",
    "If only it were facing you...",
    "\\BOh! Well done!",
    "\\BOh! It's spinning.",
    "Why, it's \\Vperfect!",
    "\\BOh! It looks yummy!",
    "\\BOh! What a weird dance.",
    "Gone fishing...",
    "\\BOh! It got a bite!",
    "It's about to pop up.",
    "I can barely see it.",
    "It's about to pop up.",
    "What a funny pose.",
    "It's about to get up.",
    "It's scratching its tummy.",
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
};

s32 D_801F4144_9A3BB4[] = {
    0x00000000,
};

f32 D_801F4148_9A3BB8[] = {
    0.0f,
    1.0f,
};

s32 D_801F4150_9A3BC0[] = {
    0x00000022,
    0x00000000,
    0x00000011,
    0x00000000,
    0x00000023,
    0x00000000,
    0x00000022,
    0x00000000,
    0x00000005,
    0x00000000,
    0x00000023,
    0x00000000,
};

s32 D_801F4180_9A3BF0[] = {
    0xFFFFFFFF,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
};

s32 D_801F4194_9A3C04 = -1;
s32 D_801F4198_9A3C08 = 0;
//??

/* Gate-level (post-synthesis, pre-placement) functional testbench for the Exp06 netlist.
 * Build: python3 gen_netlist_model.py <1_2_yosys.v> netlist_model.h && gcc -O2 -o gate_level_tb gate_level_tb.c
 * Run:   ./gate_level_tb            (QUICK=1 ./gate_level_tb skips the 590k-transaction sweep)
 * DUT = C model generated from 1_2_yosys.v (see gen_netlist_model.py).
 * Reference = Euclid-by-modulo (independent of the RTL's subtractive algorithm).
 * Checks: results, handshake protocol (monitor + scoreboard), response stability,
 *         reset at every cycle offset, held req_val, randomized valid/ready timing,
 *         and cycle latency (2n+2 cycles from accept to first resp_val). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "netlist_model.h"

static unsigned char n[NNETS];
static unsigned long long cyc = 0;
typedef struct { int req_rdy, resp_val; unsigned resp_msg; } outs;

#define FAIL(...) do { printf("[FAIL] cycle %llu: ", cyc); printf(__VA_ARGS__); printf("\n"); exit(1); } while (0)

static unsigned golden_gcd(unsigned a, unsigned b){ while (b){ unsigned t=b; b=a%b; a=t; } return a; }
static unsigned long steps(unsigned a, unsigned b){ unsigned long k=0; while (b){ if (a<b){unsigned t=a;a=b;b=t;} else a-=b; k++; } return k; }

static uint64_t rs = 0x9E3779B97F4A7C15ULL;
static uint32_t rnd(void){ rs ^= rs<<13; rs ^= rs>>7; rs ^= rs<<17; return (uint32_t)(rs>>16); }

static outs read_outs(void){
    outs o; o.req_rdy=n[N_REQ_RDY]; o.resp_val=n[N_RESP_VAL]; o.resp_msg=0;
    for (int i=0;i<16;i++) o.resp_msg |= (unsigned)n[N_RESP_MSG[i]]<<i;
    return o;
}
static void set_in(int rv, unsigned msg, int rr, int rst){
    n[N_REQ_VAL]=rv; for (int i=0;i<32;i++) n[N_REQ_MSG[i]]=(msg>>i)&1; n[N_RESP_RDY]=rr; n[N_RESET]=rst;
}
static outs peek(void){ eval_comb(n); return read_outs(); }

/* monitor / scoreboard state */
static int armed=1;
static int p_valid=0,p_rst,p_rv,p_rrdy,p_rr,p_rval; static unsigned p_rmsg;
static int outstanding=0, awaiting_first_resp=0; static unsigned exp_res; static unsigned long exp_steps; static unsigned long long acc_cyc;
static unsigned long n_accept=0,n_resp=0,n_lat=0,n_stable=0,n_reset_cycles=0;

static void monitor(outs o,int rv,unsigned msg,int rr,int rst){
    if (!armed){ /* power-up garbage state: no checks until the first reset edge has been applied */
        p_valid=0; if (rst){ outstanding=0; awaiting_first_resp=0; } return; }
    if (o.req_rdy && o.resp_val) FAIL("req_rdy and resp_val both high");
    if (p_valid){
        if (!p_rst && p_rval && !p_rr){ if (!o.resp_val || o.resp_msg!=p_rmsg) FAIL("response not stable under backpressure (was %u, now val=%d msg=%u)",p_rmsg,o.resp_val,o.resp_msg); n_stable++; }
        if (p_rst){ if (!o.req_rdy || o.resp_val) FAIL("after reset: req_rdy=%d resp_val=%d",o.req_rdy,o.resp_val); }
        if (!p_rst && p_rv && p_rrdy){ if (o.req_rdy || o.resp_val) FAIL("after accept: req_rdy=%d resp_val=%d (expected 0/0)",o.req_rdy,o.resp_val); }
        if (!p_rst && p_rval && p_rr){ if (o.resp_val || !o.req_rdy) FAIL("after response handshake: resp_val=%d req_rdy=%d (expected 0/1)",o.resp_val,o.req_rdy); }
        if (!p_rst && p_rrdy && !p_rv){ if (!o.req_rdy) FAIL("req_rdy dropped without a request"); }
    }
    if (rst){ outstanding=0; awaiting_first_resp=0; n_reset_cycles++; }
    else {
        if (awaiting_first_resp && o.resp_val){
            unsigned long long want = acc_cyc + 2*exp_steps + 2;
            if (cyc != want) FAIL("latency: first resp_val at cycle %llu, expected %llu (n=%lu)",cyc,want,exp_steps);
            if (o.resp_msg != exp_res) FAIL("result %u expected %u",o.resp_msg,exp_res);
            awaiting_first_resp=0; n_lat++;
        }
        if (rv && o.req_rdy){
            if (outstanding) FAIL("request accepted while one outstanding");
            unsigned a=(msg>>16)&0xFFFF,b=msg&0xFFFF; exp_res=golden_gcd(a,b); exp_steps=steps(a,b);
            outstanding=1; awaiting_first_resp=1; acc_cyc=cyc; n_accept++;
        }
        if (o.resp_val && rr){
            if (!outstanding) FAIL("response handshake with no outstanding request");
            if (o.resp_msg != exp_res) FAIL("response %u expected %u",o.resp_msg,exp_res);
            outstanding=0; n_resp++;
        }
    }
    p_valid=1;p_rst=rst;p_rv=rv;p_rrdy=o.req_rdy;p_rr=rr;p_rval=o.resp_val;p_rmsg=o.resp_msg;
}
static outs cycle(int rv,unsigned msg,int rr,int rst){
    set_in(rv,msg,rr,rst); eval_comb(n);
    outs o=read_outs(); monitor(o,rv,msg,rr,rst);
    unsigned char d[NFLOPS]; for (int i=0;i<NFLOPS;i++) d[i]=n[FLOP_D[i]];
    for (int i=0;i<NFLOPS;i++) n[FLOP_Q[i]]=d[i];
    if (rst) armed=1;
    cyc++; return o;
}
#define REQ(a,b) ((((unsigned)(a))<<16)|(unsigned)(b))
#define CAP 400000

static void idle(int k){ while (k-- > 0) cycle(0,0,0,0); }
static void wait_ready(void){ int c=0; while (!peek().req_rdy){ cycle(0,0,0,0); if(++c>CAP) FAIL("timeout waiting req_rdy"); } }
static void wait_resp(int rr_early){ int c=0; while (!peek().resp_val){ cycle(0,0,rr_early,0); if(++c>CAP) FAIL("timeout waiting resp_val"); } }

/* one transaction; hold = cycles of backpressure, early = resp_rdy high from accept, decoy = hold req_val high w/ other msg while busy */
static void xact(unsigned a,unsigned b,int start_delay,int hold,int early,int decoy){
    idle(start_delay); wait_ready();
    cycle(1,REQ(a,b),early,0);
    unsigned dmsg = REQ(rnd()&0xFFFF, rnd()&0xFFFF);
    if (early){ int c=0; while (!peek().resp_val){ cycle(decoy,dmsg,1,0); if(++c>CAP) FAIL("timeout"); }
        outs o=peek(); if (o.resp_msg!=golden_gcd(a,b)) FAIL("gcd(%u,%u)=%u got %u",a,b,golden_gcd(a,b),o.resp_msg);
        cycle(0,0,1,0); return; }
    int c=0; while (!peek().resp_val){ cycle(decoy,dmsg,0,0); if(++c>CAP) FAIL("timeout gcd(%u,%u)",a,b); }
    outs o=peek(); if (o.resp_msg!=golden_gcd(a,b)) FAIL("gcd(%u,%u)=%u got %u",a,b,golden_gcd(a,b),o.resp_msg);
    for (int h=0;h<hold;h++){ outs q=cycle(decoy,dmsg,0,0); if(!q.resp_val||q.resp_msg!=o.resp_msg||q.req_rdy) FAIL("hold violated"); }
    cycle(0,0,1,0);
}
/* chained: B presented (req_val held) right after A accepted; B must be accepted exactly 1 cycle after A's response fires */
static void chained(unsigned a1,unsigned b1,unsigned a2,unsigned b2,int hold){
    wait_ready(); cycle(1,REQ(a1,b1),0,0);
    int c=0; while (!peek().resp_val){ cycle(1,REQ(a2,b2),0,0); if(++c>CAP) FAIL("timeout chained A"); }
    if (peek().resp_msg!=golden_gcd(a1,b1)) FAIL("chained A wrong");
    for (int h=0;h<hold;h++) cycle(1,REQ(a2,b2),0,0);
    unsigned long before=n_accept;
    cycle(1,REQ(a2,b2),1,0);                   /* response handshake, req_val still high, not accepted (req_rdy=0) */
    if (n_accept!=before) FAIL("request accepted in the same cycle as response handshake");
    if (!peek().req_rdy) FAIL("req_rdy not high the cycle after response handshake");
    cycle(1,REQ(a2,b2),0,0);                   /* accepted now */
    if (n_accept!=before+1) FAIL("held request B not accepted one cycle after response");
    wait_resp(0); if (peek().resp_msg!=golden_gcd(a2,b2)) FAIL("chained B wrong");
    cycle(0,0,1,0);
}
static void do_reset(int cycles){ for (int i=0;i<cycles;i++) cycle(0,0,0,1); }

int main(void){
    /* S0: random power-up state, outputs Moore (independent of inputs), reset recovery */
    for (int trial=0; trial<64; trial++){
        for (int i=0;i<NNETS;i++) n[i]=rnd()&1;
        for (int i=0;i<NFLOPS;i++) n[FLOP_Q[i]]=rnd()&1;
        p_valid=0; outstanding=0; awaiting_first_resp=0; armed=0;
        set_in(0,0,0,0); outs a=peek(); set_in(1,0xFFFFFFFFu,1,0); outs b=peek();
        if (a.req_rdy!=b.req_rdy||a.resp_val!=b.resp_val||a.resp_msg!=b.resp_msg) FAIL("outputs depend combinationally on inputs");
        do_reset(1+(trial&3)); outs o=peek(); if(!o.req_rdy||o.resp_val) FAIL("not idle after power-up reset");
    }
    printf("[PASS] S0 random power-up + reset recovery (64 trials), outputs input-independent\n");

    /* S1: directed 26 */
    static const unsigned dc[26][2]={{48,18},{7,13},{16,16},{0,9},{9,0},{0,0},{0,1},{1,0},{100,100},{1,1},{256,64},{1024,512},{0,32768},
        {65521,65519},{49999,50021},{65535,65535},{60000,45000},{32760,32736},{1,65535},{65535,1},{12,8},{15,10},{21,14},{3,65535},{7,49},{13,169}};
    for (int i=0;i<26;i++) xact(dc[i][0],dc[i][1],i%3,i%4,0,0);
    printf("[PASS] S1 directed: 26 cases\n");

    /* S2: long backpressure with decoy request held high */
    static const unsigned bp[6][2]={{48,18},{0,0},{9,0},{0,9},{65535,65535},{65521,65519}};
    for (int i=0;i<6;i++) xact(bp[i][0],bp[i][1],0,40,0,1);
    printf("[PASS] S2 backpressure (40 cycles) with req_val held high: 6 cases\n");

    /* S3: chained / held req_val */
    static const unsigned ch[6][4]={{48,18,7,13},{9,0,0,9},{0,0,0,0},{16,16,100,100},{21,14,25,15},{65535,1,1,65535}};
    for (int i=0;i<6;i++) chained(ch[i][0],ch[i][1],ch[i][2],ch[i][3],i*3);
    printf("[PASS] S3 chained requests with held req_val: 6 pairs\n");

    /* S4: reset at every cycle offset of a transaction */
    static const unsigned rc[5][2]={{48,18},{7,13},{16,16},{9,0},{0,9}};
    long resets=0;
    for (int k=0;k<5;k++){
        unsigned long nn=steps(rc[k][0],rc[k][1]); int span=(int)(2*nn+6);
        for (int off=0; off<=span; off++){
            for (int w=1; w<=2; w++){
                wait_ready(); cycle(1,REQ(rc[k][0],rc[k][1]),0,0);
                for (int i=0;i<off;i++){ if (peek().resp_val) break; cycle(0,0,0,0); }   /* stop at DONE: reset while response pending */
                do_reset(w);
                outs o=peek(); if(!o.req_rdy||o.resp_val) FAIL("not idle after mid-transaction reset");
                idle(12); if (peek().resp_val) FAIL("ghost response after reset");
                xact(21,14,0,1,0,0); xact(rc[k][1]?rc[k][1]:5,rc[k][0],0,0,0,0);
                resets++;
            }
        }
    }
    /* reset coinciding with request, and reset coinciding with response handshake */
    wait_ready(); cycle(1,REQ(48,18),0,1); if(!peek().req_rdy||peek().resp_val) FAIL("reset+req_val same cycle");
    idle(20); if (peek().resp_val) FAIL("request accepted during reset");
    wait_ready(); cycle(1,REQ(48,18),0,0); wait_resp(0); cycle(0,1,1,1); if(!peek().req_rdy||peek().resp_val) FAIL("reset+resp_rdy same cycle");
    xact(30,12,0,0,0,0);
    printf("[PASS] S4 reset at every cycle offset (incl. DONE/pending response): %ld resets, reset+req_val, reset+resp_rdy\n",resets);

    /* S5: random operands, randomized valid/ready timing, early ready, decoys */
    for (int i=0;i<10000;i++){
        unsigned a,b; int cls=rnd()%5;
        if (cls==0){a=rnd()&0xFF;b=rnd()&0xFF;} else if (cls==1){a=rnd()&0xFFFF;b=rnd()&0xFF;}
        else if (cls==2){a=rnd()&0xFF;b=rnd()&0xFFFF;} else {a=rnd()&0xFFFF;b=rnd()&0xFFFF;}
        xact(a,b,rnd()%4,rnd()%7,(rnd()%5)==0,(rnd()%3)==0);
    }
    printf("[PASS] S5 randomized operands + handshake timing: 10000 transactions\n");

    /* S6: dense sweep (skipped when env QUICK is set, e.g. for mutation testing) */
    if (getenv("QUICK")) {
        printf("[SKIP] S6 dense sweep (QUICK set)\n");
    } else {
        unsigned long sw=0;
        for (unsigned ha=0;ha<3;ha++) for (unsigned hb=0;hb<3;hb++)
            for (unsigned la=0;la<256;la++) for (unsigned lb=0;lb<256;lb++){
                unsigned a=(ha<<8)|la,b=(hb<<8)|lb;
                wait_ready(); cycle(1,REQ(a,b),1,0);       /* early ready keeps the sweep fast; scoreboard checks the result */
                while(!peek().resp_val) cycle(0,0,1,0);
                cycle(0,0,1,0); sw++;
            }
        printf("[PASS] S6 dense sweep (ha,hb in {0,1,2} x all 8-bit low pairs): %lu transactions\n",sw);
    }

    /* S7: boundary operands incl. worst-case latency */
    static const unsigned bv[]={0,1,2,127,128,255,256,257,32767,32768,65534,65535};
    int nb=sizeof(bv)/sizeof(bv[0]); int cnt=0;
    for (int i=0;i<nb;i++) for (int j=0;j<nb;j++){ xact(bv[i],bv[j],0,0,1,0); cnt++; }
    printf("[PASS] S7 boundary cross product: %d transactions\n",cnt);

    printf("\nTOTAL cycles simulated: %llu | requests accepted: %lu | responses delivered: %lu | latency checks: %lu | stability checks: %lu | reset cycles: %lu\n",
        cyc,n_accept,n_resp,n_lat,n_stable,n_reset_cycles);
    printf("ALL GATE-LEVEL CHECKS PASSED\n");
    return 0;
}

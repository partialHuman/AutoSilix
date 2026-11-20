/* Exhaustive check of Exp06 split-subtractor equations over all 2^32 (a,b) pairs.
 * Transcribes gcd.v lines 74-75 (stage 1) and 86-90 (stage 2) with Verilog widths.
 * Reference is plain integer arithmetic, not the split equations.
 * Also checks the datapath commit (swap vs subtract) against the reference algorithm step. */
#include <stdio.h>
#include <stdint.h>
int main(void){
    uint64_t checked=0, bad=0, borrow_cases=0, hi_borrow_only=0, lo_borrow_ge=0;
    for (uint32_t a=0; a<65536; a++){
        for (uint32_t b=0; b<65536; b++){
            /* stage 1 */
            uint32_t a_lo=a&0xFF, b_lo=b&0xFF;
            uint32_t diff_lo=(a_lo-b_lo)&0xFF;          /* [7:0] truncation */
            uint32_t borrow_mid=(a_lo<b_lo)?1:0;
            /* stage 2: 9-bit unsigned {1'b0,a_hi}-{1'b0,b_hi}-{8'd0,borrow_mid} */
            uint32_t a_hi=a>>8, b_hi=b>>8;
            uint32_t ext=(a_hi - b_hi - borrow_mid) & 0x1FF;   /* 9-bit wrap */
            uint32_t diff_hi=ext&0xFF;
            uint32_t borrow_final=(ext>>8)&1;
            uint32_t full=((diff_hi<<8)|diff_lo)&0xFFFF;
            /* reference */
            uint32_t ref_borrow=(a<b)?1:0;
            uint32_t ref_diff=(a-b)&0xFFFF;
            /* one iteration of the subtractive algorithm per RTL commit */
            uint32_t na,nb, ra,rb;
            if (borrow_final){ na=b; nb=a; } else { na=full; nb=b; }
            if (a<b){ ra=b; rb=a; } else { ra=a-b; rb=b; }
            checked++;
            if (borrow_final!=ref_borrow || full!=ref_diff || na!=ra || nb!=rb) bad++;
            if (ref_borrow) borrow_cases++;
            if (ref_borrow && !borrow_mid) hi_borrow_only++;
            if (!ref_borrow && borrow_mid) lo_borrow_ge++;
        }
    }
    printf("pairs checked: %llu\nmismatches: %llu\n", (unsigned long long)checked,(unsigned long long)bad);
    printf("coverage: a<b cases=%llu, a<b with no low-byte borrow=%llu, a>=b with low-byte borrow (borrow-in exercised)=%llu\n",
        (unsigned long long)borrow_cases,(unsigned long long)hi_borrow_only,(unsigned long long)lo_borrow_ge);
    return bad?1:0;
}

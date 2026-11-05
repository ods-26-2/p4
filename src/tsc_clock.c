#include <stdint.h>
#include <time.h>

static int64_t timespec_to_ns(struct timespec t) {
    return (int64_t)t.tv_sec * 1000000000LL + t.tv_nsec;
}

int64_t p4_tsc_raw_offset_ns(void) {
    struct timespec antes, depois;
    uint64_t ciclos, frequencia;

    if (clock_gettime(CLOCK_MONOTONIC_RAW, &antes) != 0)
        return -1;

    __asm__ volatile("isb" ::: "memory");
    __asm__ volatile("mrs %0, cntvct_el0" : "=r"(ciclos));
    __asm__ volatile("mrs %0, cntfrq_el0" : "=r"(frequencia));

    if (clock_gettime(CLOCK_MONOTONIC_RAW, &depois) != 0)
        return -1;

    if (frequencia == 0)
        return -1;

    uint64_t tsc_ns = (uint64_t)(
        ((__uint128_t)ciclos * 1000000000ULL) / frequencia
    );

    int64_t raw_ns = (
        timespec_to_ns(antes) + timespec_to_ns(depois)
    ) / 2;

    return (int64_t)tsc_ns - raw_ns;
}
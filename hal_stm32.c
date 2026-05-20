/*
 * mishmaath / BodyGuard — real HAL for STM32F407VE
 *
 * compile with: -DMISH_HAL_REAL
 * link against: STM32 HAL (stm32f4xx_hal.c etc)
 *
 * stub functions in transpiler output are guarded by #ifndef MISH_HAL_REAL
 * so this file replaces them cleanly when targeting the chip.
 */

#define MISH_HAL_REAL
#include "stm32f4xx_hal.h"

/* ADC — returns 0–4095 (12-bit)
 * pin maps to ADC channel — adjust per your wiring */
int mish_adc_read(int pin) {
    ADC_ChannelConfTypeDef cfg = {0};
    cfg.Channel      = pin;   /* pin = ADC_CHANNEL_0 etc */
    cfg.Rank         = 1;
    cfg.SamplingTime = ADC_SAMPLETIME_56CYCLES;
    HAL_ADC_ConfigChannel(&hadc1, &cfg);
    HAL_ADC_Start(&hadc1);
    HAL_ADC_PollForConversion(&hadc1, HAL_MAX_DELAY);
    return (int)HAL_ADC_GetValue(&hadc1);
}

/* GPIO — pin maps to actual GPIO pin number in your board config */
void mish_gpio_set(int pin, int val) {
    /* example: pin 5 → GPIOD pin 5 — adapt to your wiring */
    HAL_GPIO_WritePin(GPIOD, (1 << pin), val ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

int mish_gpio_get(int pin) {
    return (int)HAL_GPIO_ReadPin(GPIOD, (1 << pin));
}

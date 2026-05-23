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

/* PWM — duty 0–255, mapped to timer compare register
 * assumes TIM3 configured in PWM mode, period = 255 */
void mish_pwm_set(int pin, int duty) {
    /* pin maps to timer channel — adapt per your wiring */
    TIM_OC_InitTypeDef cfg = {0};
    cfg.OCMode     = TIM_OCMODE_PWM1;
    cfg.Pulse      = (uint32_t)duty;
    cfg.OCPolarity = TIM_OCPOLARITY_HIGH;
    cfg.OCFastMode = TIM_OCFAST_DISABLE;
    HAL_TIM_PWM_ConfigChannel(&htim3, &cfg, TIM_CHANNEL_1);
    HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
}

/* UART — assumes huart2 (USB-serial on Nucleo / USART2 on F407VE) */
void mish_uart_send(const char *msg) {
    HAL_UART_Transmit(&huart2, (uint8_t *)msg, strlen(msg), HAL_MAX_DELAY);
}

/* I2C — assumes hi2c1, addr is 7-bit (STM32 HAL left-shifts internally) */
int mish_i2c_read(int addr, int reg) {
    uint8_t buf = 0;
    HAL_I2C_Mem_Read(&hi2c1, (uint16_t)(addr << 1), (uint16_t)reg,
                     I2C_MEMADD_SIZE_8BIT, &buf, 1, HAL_MAX_DELAY);
    return (int)buf;
}

int mish_i2c_read16(int addr, int reg) {
    uint8_t buf[2] = {0};
    HAL_I2C_Mem_Read(&hi2c1, (uint16_t)(addr << 1), (uint16_t)reg,
                     I2C_MEMADD_SIZE_8BIT, buf, 2, HAL_MAX_DELAY);
    return (int)(int16_t)((buf[0] << 8) | buf[1]);
}

void mish_i2c_write(int addr, int reg, int val) {
    uint8_t buf = (uint8_t)val;
    HAL_I2C_Mem_Write(&hi2c1, (uint16_t)(addr << 1), (uint16_t)reg,
                      I2C_MEMADD_SIZE_8BIT, &buf, 1, HAL_MAX_DELAY);
}

void mish_uart_recv(char *buf, int sz) {
    /* read until newline or buffer full */
    int i = 0;
    uint8_t b;
    while (i < sz - 1) {
        if (HAL_UART_Receive(&huart2, &b, 1, HAL_MAX_DELAY) != HAL_OK) break;
        if (b == '\n') break;
        buf[i++] = (char)b;
    }
    buf[i] = 0;
}

/* interrupt — EXTI falling-edge on pin, calls registered mishmaath handler */
#define MISH_MAX_IRQ 16
static void (*_mish_irq_table[MISH_MAX_IRQ])(void);

void mish_interrupt_register(int pin, void (*cb)(void)) {
    if (pin < 0 || pin >= MISH_MAX_IRQ) return;
    _mish_irq_table[pin] = cb;
    GPIO_InitTypeDef cfg = {0};
    cfg.Pin   = (uint16_t)(1u << pin);
    cfg.Mode  = GPIO_MODE_IT_FALLING;
    cfg.Pull  = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOD, &cfg);
    IRQn_Type irqn = (IRQn_Type)(EXTI0_IRQn + pin);
    HAL_NVIC_SetPriority(irqn, 0, 0);
    HAL_NVIC_EnableIRQ(irqn);
}

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin) {
    int pin = __builtin_ctz(GPIO_Pin);
    if (pin < MISH_MAX_IRQ && _mish_irq_table[pin])
        _mish_irq_table[pin]();
}

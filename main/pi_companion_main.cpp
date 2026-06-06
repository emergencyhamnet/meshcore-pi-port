#include "../platform/pi_board.h"
#include "../platform/pi_gpio.h"
#include "../platform/pi_spi.h"
#include "../platform/pi_storage.h"

int main() {
    if (!pi_port::board_bootstrap()) {
        return 1;
    }

    if (!pi_port::gpio_init()) {
        return 2;
    }

    if (!pi_port::spi_init()) {
        return 3;
    }

    if (!pi_port::storage_init()) {
        return 4;
    }

    return 0;
}
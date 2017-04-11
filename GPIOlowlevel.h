#ifndef GPIOLOWLEVEL_H
#define GPIOLOWLEVEL_H

/* wiringPi replacement stuff  - just use the low level bits that we want, when we want them
last modified 2017/02/17 by Jamie Boyd */
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

/*The CPU of Raspberry Pi 1 is Broadcom BCM2835, and the peripheral addresses start
from 0x20000000. The CPU of Raspberry Pi 2 is Broadcom BCM2836, and the peripheral 
addresses starts from 0x3F000000. The Raspberry Pi 3 is Broadcom BCM2837 but has
the same peripheral address start as the Raspberry Pi 2. We first define which
Raspberry Pi board to use. Define RPI2 if using a Raspberry Pi 3
Take care to have defined only one at time. So comment out exactly one of the following 2 lines */
//#define RPI
#define RPI2

/*We define a constant BCM_PERI_BASE that contains the base of all peripherals'
physical address. Different peripherals are defined by an offset to the base physical address. */
#ifdef RPI
#define BCM_PERI_BASE	0x20000000
#endif
#ifdef RPI2
#define BCM_PERI_BASE	0x3F000000
#endif

/*GPIO_BASE is the base address of GPIO peripherals, and its offset from the physical address is 0x200000.*/
#define GPIO_BASE       	(BCM_PERI_BASE + 0x200000)	// GPIO controller
/*PWM_BASE and CLOCK_BASE are defined by 0x20C000 and 0x101000 offsets 
from the base peripheral addresss */
#define PWM_BASE			(BCM_PERI_BASE + 0x20C000)
#define CLOCK_BASE			(BCM_PERI_BASE + 0x101000)

/* GPU Clock */
#define GPU_CLOCK1          (0x7E801000 - 0x7E000000 + BCM_PERI_BASE)
#define GPU_CLOCK2          0x3F801000
#define GPU_CLOCK3          0x3F003000

/* PWM control registers addresses are defined by an offset to PWM_BASE. */
#define PWM_CTL 0             // PWM Control
#define PWM_RNG0 4            // PWM Channel 0 Range
#define PWM_DAT0 5            // PWM Channel 0 Data
#define PWM_RNG1 8            // PWM Channel 1 Range
#define PWM_DAT1 9            // PWM Channel 1 Data
#define PWMCLK_CNTL 40        // PWM Clock Control
#define PWMCLK_DIV 41         // PWM Clock Divisor

/*Frequency of oscillator that we use as source for PWM clock*/
#define PI_CLOCK_RATE 19.2e6	//19.2 Mhz
/*In addition, we need to define the page and block size in the memory, so every time mmap() is called with 4KB.*/
#define PAGE_SIZE 		4096
#define BLOCK_SIZE 	4096

/* values for setting some registers need to ORed with this magic number, the clock manager password */
#define	BCM_PASSWORD		0x5A000000

/*macros that can be used for setting and unsetting bits in registers relative to gpio memory mapping*/
#define INP_GPIO(gpio,g) *(gpio+((g)/10)) &= ~(7<<(((g)%10)*3)) 	// sets a GPIO pin as input, clearing bits, so useful as a "cleanser"
#define OUT_GPIO(gpio,g) *(gpio+((g)/10)) |=  (1<<(((g)%10)*3))		// sets a GPIO pin as output
#define SET_GPIO_ALT(gpio,g,a) *(gpio+(((g)/10))) |= (((a)<=3?(a)+4:(a)==4?3:2)<<(((g)%10)*3))
#define GPIO_SET(gpio)	*(gpio + 7)  // sets bits which are 1 ignores bits which are 0
#define GPIO_CLR(gpio) 	*(gpio + 10) // clears bits which are 1 ignores bits which are 0

// Structure for access to low level memory
typedef struct bcm_peripheral {
    unsigned long addr_p;
    int mem_fd;
    void *map;
    volatile unsigned int *addr;
} bcm_peripheral, *bcm_peripheralPtr;

/*Define GPIOperi in one .cpp file */
extern bcm_peripheralPtr GPIOperi;

/*This function takes a pointer to bcm_peripheral struct, p, whose addr_p field should be set
to the base addresss of the peripheral you wish to control. It maps the low level memory
of the peripheral and fills out the rest of the fields in the bcm_peripheral struct.
Low level memory for GPIO can be accessed through the new /dev/gpiomem interface
which does not require root access. Unfortunately, the PWM and clock hardware are
NOT accessible through /dev/gpiomem, and must be accessed through /dev/mem,
which requires running your programs with sudo or gksu to get root access.
Trying to access PWM registers through /dev/gpiomem WILL CRASH YOUR PI  
The memInterface paramater determines which method to use. 
*/
#define IFACE_DEV_GPIOMEM	1	// use this only for GPIO
#define IFACE_DEV_MEM		0	// use this for GPIO or PWM and/or clock access
inline int map_peripheral(bcm_peripheralPtr p, int memInterface){
	if (memInterface == IFACE_DEV_GPIOMEM){
		// Open newfangled dev/gpiomem instead of /dev/mem for access without sudo
		if ((p->mem_fd = open("/dev/gpiomem", O_RDWR|O_SYNC) ) < 0) {
			perror("Failed to open /dev/gpiomem");
			return 1;
		}
	}else{
		if ((p->mem_fd = open("/dev/mem", O_RDWR|O_SYNC) ) < 0) {
			perror("Failed to open /dev/mem. Did you forget to sudo");
			return 1;
		}
	}	
	/* mmap IO */
	p->map = mmap(
		NULL,							//Any address in our space will do
		BLOCK_SIZE,						//Map length
		PROT_READ|PROT_WRITE|PROT_EXEC,	// Enable reading & writing to mapped memory
		MAP_SHARED| MAP_LOCKED,			//Shared with other processes
		p->mem_fd,						//File to map
		p->addr_p						//Offset to base address
	);
	//p->map = mmap(NULL, BLOCK_SIZE, PROT_READ|PROT_WRITE, MAP_SHARED, p->mem_fd, p->addr_p);
	if (p->map == MAP_FAILED) {
		perror("mmap error");
		close (p->mem_fd);
		return 1;
	}
	p ->addr = (volatile unsigned int *)p->map;
	// close file descriptor
	if (close(p -> mem_fd) < 0){
		perror("couldn't close memory file descriptor");
		return 1;
	}
	return 0;
}

inline void unmap_peripheral(bcm_peripheralPtr p) {
	munmap(p->map, BLOCK_SIZE);
}
#endif

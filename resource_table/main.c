#include <stdio.h>
#include <stdlib.h>
#include "resource_table.h"

int main( int argc, char *argv[] ){
    int ret;
    FILE *fp = NULL;
    void *dtb = NULL;
    int   dtb_size = 0;

    if( argc != 2 ){
        printf("Usage:\n");
        printf("  %s <dtb>\n", argv[0]);
        return 1;
    }

    fp = fopen(argv[1], "rb");
    if( fp == NULL ){
        printf("open %s failed.\n", argv[1]);
        return 1;
    }
    fseek(fp, 0, SEEK_END);
    dtb_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);

    if( dtb_size <= 0 ){
        return 1;
    }

    dtb = malloc(dtb_size);
    if( dtb == NULL ){
        printf("no memory\n");
        return 1;
    }
    if( fread(dtb, dtb_size, 1, fp) != 1 ){
        printf("read failed.\n");
        return 1;
    }

    ret = resource_table_init( dtb, dtb_size );
    if( ret < 0 ){
        printf("init failed.\n");
        return 1;
    }

    resource_table_dump();


    printf("cell name: %s\n", resource_table_cell_name() );
    printf("cpu name : %s\n", resource_table_cpu_name() );
    int mem_count = resource_table_memory_count();
    printf("memory count : %d\n", mem_count );
    for( int i=0; i<mem_count; ++i ){
        uint64_t phys, virt, size;
        ret = resource_table_memory_at( i, &phys, &virt, &size );
        if( ret < 0 ){
            return 1;
        }
        printf("  [%d] phys: 0x%lx\n", i, phys );
        printf("      virt: 0x%lx\n", virt );
        printf("      size: 0x%lx\n", size );
    }

    int dev_count = resource_table_device_count();
    printf("device count: %d\n", dev_count);
    for( int i=0; i<dev_count; ++i ){
        printf( "  [%d] %s\n", i, resource_table_device_name(i) );
    }

    return 0;
}

#include <stdio.h>
#include "resource_table.h"
#include "libfdt/libfdt.h"

#define _LOG_INFO(fmt, args...) printf(fmt "\n", ##args)
#define _LOG_ERR(fmt, args...)  printf(fmt "\n", ##args)

static void *resource = NULL;

int resource_table_init( void *data, int len ){
    int ret;

    ret = fdt_check_header(data);
    if( ret < 0 ){
        return ret;
    }
    ret = fdt_check_full(data, len);
    if( ret < 0 ){
        return ret;
    }

    resource = data;
    return 0;
}

void resource_table_dump( void ){
    int ret;
    int offset;
    int node;

    if( resource == NULL ){
        return;
    }

    node = 0;
    while( 1 ){
        int prop;
        fdt_for_each_property_offset(prop, resource, node){
            const struct fdt_property *property = fdt_get_property_by_offset( resource, prop, NULL );
            const char *prop_name;
            fdt_getprop_by_offset( resource, prop, &prop_name, NULL );
            printf("  %s\n", prop_name);
        }

        int depth = 0;
        node = fdt_next_node( resource, node, &depth);
        if( node < 0 ){
            break;
        }
        const char *name = fdt_get_name(resource, node, 0);
        if( name == NULL ){
            break;
        }
        printf("%s\n", name);
    }
}

const char *resource_table_cell_name( void ){
    int ret;
    int offset;

    if( resource == NULL ){
        return NULL;
    }

    ret = fdt_check_header(resource);
    if( ret < 0 ){
        _LOG_INFO("check header failed.");
        return NULL;
    }

    offset = fdt_path_offset(resource, "/");
    const char *name = fdt_getprop(resource, offset, "cell_name", NULL);
    return name;
}

const char *resource_table_cpu_name( void ){
    int ret;
    int offset;

    if( resource == NULL ){
        return NULL;
    }

    ret = fdt_check_header(resource);
    if( ret < 0 ){
        _LOG_INFO("check header failed.");
        return NULL;
    }

    offset = fdt_path_offset(resource, "/");
    const char *name = fdt_getprop(resource, offset, "cpu_name", NULL);
    return name;
}

static int resource_table_get_value( int node, const char *name, int cells, uint64_t *value ){
    int len;
    const void *prop = NULL;

    if( cells != 1 && cells != 2 ){
        return -1;
    }

    prop = fdt_getprop( resource, node, name, &len );
    if( prop == NULL || len != cells*4 ){
        return -1;
    }

    if( cells == 1 ){
        if( value ){
            *value = fdt32_to_cpu( *(fdt32_t*)prop );
        }
    }
    else if( cells == 2 ){
        if( value ){
            *value = fdt64_to_cpu( *(fdt64_t*)prop );
        }
    }
    return 0;
}

int resource_table_memory_count( void ){
    int node = 0;
    int subnode = 0;
    int count = 0;
    int cells = 0;
    if( resource == NULL ){
        return -1;
    }

    node = fdt_path_offset( resource, "/memorys");
    if( node < 0 ){
        _LOG_ERR("/memorys not found.");
        return -1;
    }

    cells = fdt_address_cells( resource, node );
    if( cells < 0 ){
        _LOG_ERR("invalid address cells.");
        return -1;
    }

    fdt_for_each_subnode(subnode, resource, node){
        /* 检查是否有效 */
        if( resource_table_get_value(subnode, "phys", cells, NULL) < 0 ){
            return -1;
        }
        if( resource_table_get_value(subnode, "virt", cells, NULL) < 0 ){
            return -1;
        }
        if( resource_table_get_value(subnode, "size", cells, NULL) < 0 ){
            return -1;
        }
        count++;
    }

    return count;
}


int resource_table_memory_at( int index, uint64_t *phys, uint64_t *virt, uint64_t *size ){
    int ret = 0;
    int node = 0;
    int subnode = 0;
    int count = 0;
    int cells = 0;
    if( resource == NULL ){
        return -1;
    }

    node = fdt_path_offset( resource, "/memorys");
    if( node < 0 ){
        _LOG_ERR("/memorys not found.");
        return -1;
    }

    cells = fdt_address_cells( resource, node );
    if( cells < 0 ){
        _LOG_ERR("invalid address cells.");
        return -1;
    }

    fdt_for_each_subnode(subnode, resource, node){
        if( count != index ){
            count++;
            continue;
        }

        int len;
        const void *prop = NULL;

        ret = resource_table_get_value( subnode, "phys", cells, phys );
        if( ret < 0 ){
            return -1;
        }
        ret = resource_table_get_value( subnode, "virt", cells, virt );
        if( ret < 0 ){
            return -1;
        }
        ret = resource_table_get_value( subnode, "size", cells, size );
        if( ret < 0 ){
            return -1;
        }

        return 0;
    }
    return -1;
}

int resource_table_device_count( void ){
    int node = 0;
    int count = 0;
    int subnode = 0;

    if( resource == NULL ){
        return -1;
    }

    node = fdt_path_offset( resource, "/devices");
    if( node < 0 ){
        _LOG_ERR("/devices not found.");
        return -1;
    }

    fdt_for_each_subnode(subnode, resource, node){
        count++;
    }

    return count;
}

static int resource_table_device_node_at( int idx ){
    int node = 0;
    int count = 0;
    int subnode = 0;

    if( resource == NULL ){
        return -1;
    }

    node = fdt_path_offset( resource, "/devices");
    if( node < 0 ){
        _LOG_ERR("/devices not found.");
        return -1;
    }
    fdt_for_each_subnode(subnode, resource, node){
        if( count == idx ){
            return subnode;
        }
        count++;
    }

    return -1;
}

const char *resource_table_device_name( int idx ){
    int node = resource_table_device_node_at( idx );
    if( node < 0 ){
        return NULL;
    }
    return fdt_get_name( resource, node, NULL );
}

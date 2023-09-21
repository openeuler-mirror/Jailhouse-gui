#ifndef _H_RESOURCE_TABLE_
#define _H_RESOURCE_TABLE_

#include <stdint.h>

/**
 * @brief 初始化资源表
 * 调用该函数完成初始化，初始化后才可调用其他函数
 * @param resource 资源表起始地址
 * @param len 资源表长度
 * @return int 成功返回0,失败返回负数
 */
int resource_table_init( void *resource, int len );

/**
 * @brief 打印资源表内容
 * 用于测试
 */
void resource_table_dump( void );

/**
 * @brief 获取cell名称
 * @return const char*
 */
const char *resource_table_cell_name( void );

/**
 * @brief 获取cpu名称
 * @return const char*
 */
const char *resource_table_cpu_name( void );

/**
 * @brief 获取memory个数
 * @return int 成功返回memory个数，失败返回负数
 */
int resource_table_memory_count( void );

/**
 * @brief 获取内存信息
 * @param index 索引，从0到 resource_table_memory_count()-1
 * @param phys 物理地址
 * @param virt 虚拟地址
 * @param size 大小
 * @return int 成功返回0,失败返回负数
 */
int resource_table_memory_at( int index, uint64_t *phys, uint64_t *virt, uint64_t *size );

/**
 * @brief 获取设备个数
 * @return int 成功返回设备个数，失败返回负数
 */
int resource_table_device_count( void );

const char *resource_table_device_name( int idx );

#endif

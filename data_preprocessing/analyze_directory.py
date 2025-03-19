import pandas as pd
import re
import os
from collections import Counter

def analyze_topology_data(file_path="datasets/raw/xbxa_dc4_topology.xlsx"):
    """全面分析拓扑数据文件，包括所有实体类型及其命名规则"""
    print(f"正在分析文件: {file_path}")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 文件 '{file_path}' 不存在")
        return
    
    # 读取Excel文件
    try:
        df = pd.read_excel(file_path)
        print(f"成功读取文件，共 {len(df)} 行，{len(df.columns)} 列")
    except Exception as e:
        print(f"读取文件失败: {str(e)}")
        return
    
    # 打印所有列名，了解数据结构
    print("\n文件包含的列名:")
    for col in df.columns:
        print(f"- {col}")
    
    # 分析各类实体
    analyze_virtual_machines(df)
    analyze_network_elements(df)
    analyze_tenants(df)
    analyze_hosts(df)
    analyze_host_groups(df)
    analyze_storage_pools(df)
    
    # 分析实体间关系
    analyze_entity_relationships(df)

def analyze_virtual_machines(df):
    """分析虚拟机命名规则和属性"""
    print("\n==== 虚拟机分析 ====")
    
    # 确定虚拟机名称列
    vm_col = identify_column(df, ['虚拟机名称', '虚拟机', 'VM名称', 'VM'])
    
    if vm_col:
        # 获取唯一的虚拟机名称
        vm_names = df[vm_col].dropna().unique()
        print(f"共发现 {len(vm_names)} 个唯一虚拟机")
        
        # 显示前5个示例
        print("\n虚拟机名称示例:")
        for name in vm_names[:5]:
            print(f"- {name}")
        
        # 分析命名模式
        analyze_naming_pattern(vm_names, entity_type="虚拟机")
        
        # 提取虚拟机类型
        extract_vm_types(vm_names)
    else:
        print("未找到虚拟机名称列")

def analyze_network_elements(df):
    """分析网元命名规则和属性"""
    print("\n==== 网元分析 ====")
    
    # 确定网元名称列
    ne_col = identify_column(df, ['网元名称', '网元', 'NE名称', 'NE'])
    
    if ne_col:
        # 获取唯一的网元名称
        ne_names = df[ne_col].dropna().unique()
        print(f"共发现 {len(ne_names)} 个唯一网元")
        
        # 显示前5个示例
        print("\n网元名称示例:")
        for name in ne_names[:5]:
            print(f"- {name}")
        
        # 分析命名模式
        analyze_naming_pattern(ne_names, entity_type="网元")
        
        # 提取网元类型
        extract_ne_types(ne_names)
    else:
        print("未找到网元名称列")

def analyze_tenants(df):
    """分析租户命名规则和属性"""
    print("\n==== 租户分析 ====")
    
    # 确定租户名称列
    tenant_col = identify_column(df, ['租户名称', '租户', 'Tenant名称', 'Tenant'])
    
    if tenant_col:
        # 获取唯一的租户名称
        tenant_names = df[tenant_col].dropna().unique()
        print(f"共发现 {len(tenant_names)} 个唯一租户")
        
        # 显示所有租户
        print("\n租户名称:")
        for name in tenant_names:
            print(f"- {name}")
        
        # 分析命名模式
        analyze_naming_pattern(tenant_names, entity_type="租户")
    else:
        print("未找到租户名称列")

def analyze_hosts(df):
    """分析主机命名规则和属性"""
    print("\n==== 主机分析 ====")
    
    # 确定主机名称列
    host_col = identify_column(df, ['主机名称', '主机', 'Host名称', 'Host'])
    
    if host_col:
        # 获取唯一的主机名称
        host_names = df[host_col].dropna().unique()
        print(f"共发现 {len(host_names)} 个唯一主机")
        
        # 显示前5个示例
        print("\n主机名称示例:")
        for name in host_names[:5]:
            print(f"- {name}")
        
        # 分析命名模式
        analyze_naming_pattern(host_names, entity_type="主机")
        
        # 分析主机资源情况
        if 'CPU核数' in df.columns and '内存大小(GB)' in df.columns:
            print("\n主机资源统计:")
            print(f"平均CPU核数: {df['CPU核数'].mean():.2f}")
            print(f"平均内存大小: {df['内存大小(GB)'].mean():.2f} GB")
    else:
        print("未找到主机名称列")

def analyze_host_groups(df):
    """分析主机组命名规则和属性"""
    print("\n==== 主机组分析 ====")
    
    # 确定主机组名称列
    group_col = identify_column(df, ['主机组名称', '主机组', 'HostGroup名称', 'HostGroup'])
    
    if group_col:
        # 获取唯一的主机组名称
        group_names = df[group_col].dropna().unique()
        print(f"共发现 {len(group_names)} 个唯一主机组")
        
        # 显示所有主机组
        print("\n主机组名称:")
        for name in group_names:
            print(f"- {name}")
        
        # 分析命名模式
        analyze_naming_pattern(group_names, entity_type="主机组")
    else:
        print("未找到主机组名称列")

def analyze_storage_pools(df):
    """分析存储池命名规则和属性"""
    print("\n==== 存储池分析 ====")
    
    # 确定存储池名称列
    pool_col = identify_column(df, ['存储池名称', '存储池', 'StoragePool名称', 'StoragePool'])
    
    if pool_col:
        # 获取唯一的存储池名称
        pool_names = df[pool_col].dropna().unique()
        print(f"共发现 {len(pool_names)} 个唯一存储池")
        
        # 显示所有存储池
        print("\n存储池名称:")
        for name in pool_names:
            print(f"- {name}")
        
        # 分析命名模式
        analyze_naming_pattern(pool_names, entity_type="存储池")
        
        # 分析存储池容量
        if '存储池容量(GB)' in df.columns and '存储池已用容量(GB)' in df.columns:
            print("\n存储池资源统计:")
            print(f"平均存储池容量: {df['存储池容量(GB)'].mean():.2f} GB")
            print(f"平均存储池使用率: {df['存储池已用容量(GB)'].sum() / df['存储池容量(GB)'].sum() * 100:.2f}%")
    else:
        print("未找到存储池名称列")

def analyze_entity_relationships(df):
    """分析实体间的关系"""
    print("\n==== 实体关系分析 ====")
    
    # 根据实际列名分析关系
    # 例如：虚拟机与主机的关系
    vm_col = identify_column(df, ['虚拟机名称', '虚拟机', 'VM名称', 'VM'])
    host_col = identify_column(df, ['主机名称', '主机', 'Host名称', 'Host'])
    
    if vm_col and host_col:
        # 分析每个主机上的虚拟机数量
        vm_per_host = df.groupby(host_col)[vm_col].nunique()
        print(f"\n每个主机平均承载 {vm_per_host.mean():.2f} 个虚拟机")
        print(f"最多的主机承载 {vm_per_host.max()} 个虚拟机")
    
    # 其他关系分析可根据实际列名添加

def identify_column(df, possible_names):
    """根据可能的列名找到匹配的列"""
    for name in possible_names:
        for col in df.columns:
            if name in col:
                return col
    return None

def analyze_naming_pattern(names, entity_type, sample_size=10):
    """分析命名模式"""
    print(f"\n{entity_type}命名模式分析:")
    
    # 分析长度
    lengths = [len(str(name)) for name in names]
    print(f"名称长度: 最小 {min(lengths)}，最大 {max(lengths)}，平均 {sum(lengths)/len(lengths):.2f}")
    
    # 分析分隔符
    separators = []
    for name in names:
        name_str = str(name)
        if '-' in name_str:
            separators.append('-')
        if '_' in name_str:
            separators.append('_')
        if '.' in name_str:
            separators.append('.')
    
    separator_counts = Counter(separators)
    if separator_counts:
        print("常见分隔符:", end=" ")
        for sep, count in separator_counts.most_common():
            print(f"'{sep}' ({count}次)", end=", ")
        print()
    
    # 分析前缀模式
    prefixes = []
    for name in names:
        name_str = str(name)
        parts = re.split(r'[-_.]', name_str)
        if parts:
            prefixes.append(parts[0])
    
    prefix_counts = Counter(prefixes)
    print("常见前缀:", end=" ")
    for prefix, count in prefix_counts.most_common(3):
        print(f"'{prefix}' ({count}次)", end=", ")
    print()

def extract_vm_types(vm_names, sample_size=10):
    """提取虚拟机类型"""
    print("\n虚拟机类型分析:")
    
    # 使用正则表达式提取类型标识
    vm_types = []
    for name in vm_names:
        name_str = str(name)
        # 尝试匹配类似 -OMU-0, -SIG-1 等模式
        type_match = re.search(r'-([A-Z]{2,6})-\d+$', name_str)
        if type_match:
            vm_types.append(type_match.group(1))
    
    # 统计类型分布
    type_counts = Counter(vm_types)
    if type_counts:
        print("识别出的虚拟机类型:")
        for vm_type, count in type_counts.most_common():
            print(f"- {vm_type}: {count}个虚拟机")
    else:
        print("未能从名称中提取出明确的虚拟机类型")

def extract_ne_types(ne_names):
    """提取网元类型"""
    print("\n网元类型分析:")
    
    # 5G核心网常见网元类型
    ne_type_patterns = [
        "AMF", "SMF", "UPF", "PCF", "UDM", "AUSF", "NRF", "NEF", "NSSF",
        "IMS", "HSS", "MME", "PCRF", "SGW", "PGW"
    ]
    
    # 查找网元名称中的类型标识
    ne_types = []
    for name in ne_names:
        name_str = str(name)
        found_type = None
        
        # 尝试匹配已知网元类型
        for pattern in ne_type_patterns:
            if pattern in name_str:
                found_type = pattern
                break
        
        # 如果没找到，尝试其他模式
        if not found_type:
            # 尝试匹配格式如 XBXAgsAMF 中的网元类型
            gs_match = re.search(r'gs([A-Z][A-Za-z]+)', name_str)
            if gs_match:
                found_type = gs_match.group(1)
        
        if found_type:
            ne_types.append(found_type)
    
    # 统计类型分布
    type_counts = Counter(ne_types)
    if type_counts:
        print("识别出的网元类型:")
        for ne_type, count in type_counts.most_common():
            print(f"- {ne_type}: {count}个网元")
    else:
        print("未能从名称中提取出明确的网元类型")

if __name__ == "__main__":
    analyze_topology_data()

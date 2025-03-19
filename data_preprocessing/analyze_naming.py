import pandas as pd
import re
from collections import Counter

# 加载Excel文件
def analyze_naming_patterns():
    print("开始分析命名模式...")
    df = pd.read_excel('../datasets/raw/xbxa_dc4_topology.xlsx')
    
    # 分析各列的命名模式
    name_columns = ['租户名称', '网元名称', '虚拟机名称', '主机名称', '主机组名称', '存储池名称']
    
    for column in name_columns:
        print(f"\n{'='*50}")
        print(f"{column}分析:")
        print(f"{'='*50}")
        
        # 获取唯一值
        unique_values = pd.unique(df[column])
        print(f"唯一值数量: {len(unique_values)}")
        
        # 打印前几个示例
        print("\n前5个示例:")
        for i, name in enumerate(unique_values[:500]):
            print(f"{i+1}. {name}")
        
        # 分析命名模式中的大致格式
        patterns = []
        for name in unique_values:
            if pd.isna(name):
                continue
                
            parts = name.split('-')
            pattern = len(parts)
            patterns.append(pattern)
        
        # 统计各种模式的数量
        pattern_counts = Counter(patterns)
        print("\n命名模式分段数量统计:")
        for pattern, count in pattern_counts.most_common():
            print(f"{pattern}段: {count}个")
        
        # 提取关键特征
        if column == '租户名称':
            # 提取省份和业务类型
            provinces = []
            business_types = []
            
            for name in unique_values:
                if pd.isna(name):
                    continue
                    
                parts = name.split('-')
                if len(parts) >= 7:
                    provinces.append(parts[6])
                if len(parts) >= 8:
                    business_types.append(parts[7])
            
            print("\n省份分布:")
            for province, count in Counter(provinces).most_common():
                print(f"{province}: {count}个")
                
            print("\n业务类型分布:")
            for business, count in Counter(business_types).most_common():
                print(f"{business}: {count}个")
                
        elif column == '网元名称':
            # 提取网元类型
            ne_types = []
            provinces = []
            
            for name in unique_values:
                if pd.isna(name):
                    continue
                    
                # 提取省份信息
                province_match = re.search(r'(gs|sn|nx|qh)', name.lower())
                if province_match:
                    provinces.append(province_match.group())
                
                # 提取网元类型
                ne_type_match = re.search(r'[A-Z]{2,}', name[10:] if len(name) > 10 else name)
                if ne_type_match:
                    ne_types.append(ne_type_match.group())
            
            print("\n网元类型分布:")
            for ne_type, count in Counter(ne_types).most_common():
                print(f"{ne_type}: {count}个")
                
            print("\n省份分布:")
            for province, count in Counter(provinces).most_common():
                print(f"{province}: {count}个")
                
        elif column == '虚拟机名称':
            # 提取功能类型
            vm_functions = []
            provinces = []
            
            for name in unique_values:
                if pd.isna(name):
                    continue
                    
                parts = name.split('-')
                if len(parts) >= 10:
                    # 提取功能类型
                    function = parts[9].split('_')[0] if '_' in parts[9] else parts[9]
                    vm_functions.append(function)
                
                # 提取省份信息
                province_match = re.search(r'(gs|sn|nx|qh)', name.lower())
                if province_match:
                    provinces.append(province_match.group())
            
            print("\n虚拟机功能类型分布:")
            for function, count in Counter(vm_functions).most_common():
                print(f"{function}: {count}个")
                
            print("\n省份分布:")
            for province, count in Counter(provinces).most_common():
                print(f"{province}: {count}个")
                
        elif column == '主机名称':
            # 提取主机类型
            host_types = []
            locations = []
            rooms = []
            
            for name in unique_values:
                if pd.isna(name):
                    continue
                    
                parts = name.split('-')
                if len(parts) >= 9:
                    host_types.append(parts[8])
                if len(parts) >= 4:
                    locations.append(parts[3])
                if len(parts) >= 5:
                    rooms.append(parts[4])
            
            print("\n主机类型分布:")
            for host_type, count in Counter(host_types).most_common():
                print(f"{host_type}: {count}个")
                
            print("\n位置分布:")
            for location, count in Counter(locations).most_common():
                print(f"{location}: {count}个")
                
            print("\n机房分布:")
            for room, count in Counter(rooms).most_common():
                print(f"{room}: {count}个")
                
        elif column == '主机组名称':
            # 提取SVIC编号
            svic_numbers = []
            locations = []
            rooms = []
            
            for name in unique_values:
                if pd.isna(name):
                    continue
                    
                # 提取SVIC编号
                svic_match = re.search(r'SVIC(\d+)', name)
                if svic_match:
                    svic_numbers.append(svic_match.group())
                
                parts = name.split('-')
                if len(parts) >= 4:
                    locations.append(parts[3])
                if len(parts) >= 5:
                    rooms.append(parts[4])
            
            print("\nSVIC编号分布:")
            for svic, count in Counter(svic_numbers).most_common():
                print(f"{svic}: {count}个")
                
            print("\n位置分布:")
            for location, count in Counter(locations).most_common():
                print(f"{location}: {count}个")
                
            print("\n机房分布:")
            for room, count in Counter(rooms).most_common():
                print(f"{room}: {count}个")
                
        elif column == '存储池名称':
            # 提取TRU编号
            tru_numbers = []
            locations = []
            rooms = []
            
            for name in unique_values:
                if pd.isna(name):
                    continue
                    
                # 提取TRU编号
                tru_match = re.search(r'TRU-(\d+)|TRU(\d+)', name)
                if tru_match:
                    group = tru_match.group(1) if tru_match.group(1) else tru_match.group(2)
                    tru_numbers.append(f"TRU{group}")
                
                parts = name.split('-')
                if len(parts) >= 4:
                    locations.append(parts[3])
                if len(parts) >= 5:
                    rooms.append(parts[4])
            
            print("\nTRU编号分布:")
            for tru, count in Counter(tru_numbers).most_common():
                print(f"{tru}: {count}个")
                
            print("\n位置分布:")
            for location, count in Counter(locations).most_common():
                print(f"{location}: {count}个")
                
            print("\n机房分布:")
            for room, count in Counter(rooms).most_common():
                print(f"{room}: {count}个")

if __name__ == "__main__":
    analyze_naming_patterns() 
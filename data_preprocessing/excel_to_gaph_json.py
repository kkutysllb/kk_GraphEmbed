import pandas as pd
import json
import re
from typing import Dict, List, Set
import os

class TopologyConverter:
    def __init__(self, excel_path: str = "datasets/raw/xbxa_dc4_topology.xlsx"):
        self.excel_path = excel_path
        self.df = None
        # 定义节点层级
        self.node_levels = {
            'DC': 0,
            'TENANT': 1,
            'NE': 2,
            'VM': 3,
            'HOST': 4,
            'HOSTGROUP': 5,
            'STORAGEPOOL': 6
        }
        # 用于存储已处理的节点ID，避免重复
        self.processed_nodes: Dict[str, Set[str]] = {
            'tenant': set(),
            'ne': set(),
            'vm': set(),
            'host': set(),
            'hostgroup': set(),
            'storagepool': set()
        }
        # 用于存储已处理的边，避免重复
        self.processed_edges: Set[str] = set()
        # 存储最终的图结构
        self.graph = {
            'nodes': [],
            'edges': []
        }
        
    def extract_node_type(self, name: str, base_type: str) -> str:
        """从节点名称中提取更细致的类型信息"""
        if pd.isna(name):
            return base_type
        
        if base_type == 'TENANT':
            # NFV-P-XBXA-04A-HW-01-gs-B5G-HW 或 NFV-P-XBXA-04A-HW-01-xnq-BC5G-HW
            parts = name.split('-')
            # 提取位置代码和业务类型
            location_code = ""
            business_type = ""
            
            # 按照固定位置提取
            if len(parts) >= 8:
                location_code = parts[6].lower()  # 位置代码: gs/sn/nx/qh/xnq等
                business_type = parts[7]  # 业务类型: B5G/C5G/XLW/CAT等
            
            # 如果固定位置未提取到，尝试正则表达式
            if not location_code:
                location_match = re.search(r'(gs|sn|nx|qh|xnq)', name.lower())
                location_code = location_match.group(1) if location_match else ""
            
            if not business_type:
                business_match = re.search(r'(B5G|C5G|BC5G|XLW|CAT|IMS)', name)
                business_type = business_match.group(1) if business_match else ""
            
            # 组合类型标识
            if location_code and business_type:
                return f'TENANT_{location_code.upper()}_{business_type}'
            elif location_code:
                return f'TENANT_{location_code.upper()}'
            elif business_type:
                return f'TENANT_{business_type}'
            
            return f'TENANT_{name.replace("-", "_")}'
            
        elif base_type == 'NE':
            # APP-XBXAgsAMFm001BHW-04AHW011 等
            # 提取位置代码
            location_match = re.search(r'(gs|sn|nx|qh|xnq)', name.lower())
            location_code = location_match.group(1).upper() if location_match else ""
            
            # 提取网元类型 - 常见的5G核心网元类型
            ne_types = [
                'AMF', 'SMF', 'UPF', 'PCF', 'UDM', 'AUSF', 'NRF', 'NEF', 'NSSF', 
                'CHF', 'DRASTP', 'DRASTPDB', 'DRASTPOMU', 'DRASIP', 'IAGW', 
                'CATOMCTT', 'PUDRCSP', 'PCFCSP'
            ]
            ne_type = ""
            for nt in ne_types:
                if nt in name:
                    ne_type = nt
                    break
            
            # 组合类型标识
            if location_code and ne_type:
                return f'NE_{location_code}_{ne_type}'
            elif location_code:
                return f'NE_{location_code}'
            elif ne_type:
                return f'NE_{ne_type}'
            
            # 如果上述方法无法提取，尝试从特定部分提取特征
            parts = name.split('-')
            if len(parts) >= 2:
                # 尝试从第二段提取XBXA后的特征
                segment = parts[1]
                feature_match = re.search(r'XBXA([a-zA-Z0-9]+)', segment)
                if feature_match:
                    feature = feature_match.group(1)
                    # 提取字母部分作为特征
                    letters_match = re.search(r'([a-zA-Z]+)', feature)
                    if letters_match:
                        return f'NE_{letters_match.group(1).upper()}'
            
            # 如果没有找到有意义的特征，使用原始名称
            return f'NE_{name.replace("-", "_")}'
            
        elif base_type == 'VM':
            # NFV-R-XBXA-04A-HW-01-VM-XBXAgsAMFm001BHW-OMU-0
            
            # 1. 提取位置代码
            location_match = re.search(r'(gs|sn|nx|qh|xnq)', name.lower())
            location_code = location_match.group(1).upper() if location_match else ""
            
            # 2. 提取网元类型 - 与虚机归属的网元相关
            ne_type = ""
            for nt in ['AMF', 'SMF', 'UPF', 'PCF', 'UDM', 'AUSF', 'NRF', 'NEF', 'NSSF', 'CHF', 'IAGW', 'DRASTP']:
                if nt in name:
                    ne_type = nt
                    break
            
            # 3. 提取虚机自身功能类型
            parts = name.split('-')
            function_type = ""
            
            # 检查特定功能类型
            if len(parts) >= 10:
                function_part = parts[9]
                # 去除下划线后的部分
                function_type = function_part.split('_')[0] if '_' in function_part else function_part
                
                # 如果只是数字，尝试使用前一段
                if function_type.isdigit() and len(parts) > 10:
                    function_type = parts[8]
            
            # 特殊功能类型检查
            if 'dual_active' in name.lower():
                function_type = 'DUAL_ACTIVE'
            elif 'dual_standby' in name.lower():
                function_type = 'DUAL_STANDBY'
            elif 'cluster' in name.lower():
                function_type = 'CLUSTER'
            elif 'OMU' in name:
                function_type = 'OMU'
            elif 'SIG' in name:
                function_type = 'SIG'
            elif 'PBU' in name:
                function_type = 'PBU'
            
            # 组合类型标识，优先包含省份信息
            type_elements = []
            if location_code:
                type_elements.append(location_code)
            if ne_type:
                type_elements.append(ne_type)
            if function_type and function_type != "0":
                type_elements.append(function_type)
            
            if type_elements:
                return f'VM_{"_".join(type_elements)}'
            
            # 最后，提取VM后节点中的特征作为类型标识
            vm_index = -1
            for i, part in enumerate(parts):
                if part == 'VM':
                    vm_index = i
                    break
                
            if vm_index > 0 and vm_index + 1 < len(parts):
                feature_part = parts[vm_index + 1]
                feature_match = re.search(r'XBXA([a-zA-Z0-9]+)', feature_part)
                if feature_match:
                    feature = feature_match.group(1)
                    letters_match = re.search(r'([a-zA-Z]+)', feature)
                    if letters_match:
                        return f'VM_{letters_match.group(1).upper()}'
                    
            # 如果都没提取到，使用原始名称
            return f'VM_{name.replace("-", "_")}'
            
        elif base_type == 'HOST':
            # NFV-D-XBXA-04A-1405-0D20-S-SRV-09
            parts = name.split('-')
            
            # 提取位置、机房和类型信息
            location = parts[3] if len(parts) > 3 else ""  # XBXA
            room = parts[4] if len(parts) > 4 else ""  # 04A
            rack_info = parts[6] if len(parts) > 6 else ""  # S
            host_type = parts[8] if len(parts) > 8 else ""  # SRV
            
            # 组合类型标识
            type_elements = []
            if location:
                type_elements.append(location)
            if room:
                type_elements.append(room)
            if rack_info:
                type_elements.append(rack_info)
            if host_type:
                type_elements.append(host_type)
            
            if type_elements:
                return f'HOST_{"_".join(type_elements)}'
            
            return f'HOST_{name.replace("-", "_")}'
            
        elif base_type == 'HOSTGROUP':
            # NFV-HA-XBXA-04A-HW-01-SVIC07
            parts = name.split('-')
            
            # 提取位置、机房和SVIC编号
            location = parts[3] if len(parts) > 3 else ""  # XBXA
            room = parts[4] if len(parts) > 4 else ""  # 04A
            
            # 提取SVIC编号
            svic_match = re.search(r'(SVIC\d+)', name)
            svic = svic_match.group(1) if svic_match else ""
            
            # 组合类型标识
            type_elements = []
            if location:
                type_elements.append(location)
            if room:
                type_elements.append(room)
            if svic:
                type_elements.append(svic)
            
            if type_elements:
                return f'HOSTGROUP_{"_".join(type_elements)}'
            
            return f'HOSTGROUP_{name.replace("-", "_")}'
            
        elif base_type == 'STORAGEPOOL':
            # NFV-DSP-XBXA-04A-HW-01-TRU-02
            parts = name.split('-')
            
            # 提取位置、机房和TRU编号
            location = parts[3] if len(parts) > 3 else ""  # XBXA
            room = parts[4] if len(parts) > 4 else ""  # 04A
            
            # 提取TRU编号
            tru_match = re.search(r'TRU-(\d+)', name)
            tru = f"TRU{tru_match.group(1)}" if tru_match else ""
            
            if not tru:
                tru_match = re.search(r'TRU(\d+)', name)
                tru = f"TRU{tru_match.group(1)}" if tru_match else ""
            
            # 组合类型标识
            type_elements = []
            if location:
                type_elements.append(location)
            if room:
                type_elements.append(room)
            if tru:
                type_elements.append(tru)
            
            if type_elements:
                return f'STORAGEPOOL_{"_".join(type_elements)}'
            
            return f'STORAGEPOOL_{name.replace("-", "_")}'
        
        return base_type
        
    def load_data(self):
        """加载Excel数据"""
        try:
            self.df = pd.read_excel(self.excel_path)
            print(f"成功加载数据，共 {len(self.df)} 行")
        except Exception as e:
            print(f"加载数据失败: {str(e)}")
            raise

    def create_dc_node(self):
        """创建数据中心根节点"""
        dc_node = {
            'id': 'DC_XBXA_DC4',
            'type': 'DC',
            'level': self.node_levels['DC'],
            'properties': {
                'name': 'XBXA_DC4'
            }
        }
        self.graph['nodes'].append(dc_node)

    def process_nodes(self):
        """处理所有节点"""
        # 首先创建DC节点
        self.create_dc_node()
        
        # 遍历每一行数据
        for _, row in self.df.iterrows():
            self.process_tenant_node(row)
            self.process_ne_node(row)
            self.process_vm_node(row)
            self.process_host_node(row)
            self.process_hostgroup_node(row)
            self.process_storagepool_node(row)

    def process_tenant_node(self, row):
        """处理租户节点"""
        tenant_name = str(row['租户名称'])
        tenant_id = f"TENANT_{tenant_name}"
        if tenant_id not in self.processed_nodes['tenant']:
            tenant_node = {
                'id': tenant_id,
                'type': self.extract_node_type(tenant_name, 'TENANT'),
                'level': self.node_levels['TENANT'],
                'properties': {
                    'name': tenant_name
                }
            }
            self.graph['nodes'].append(tenant_node)
            # 添加与DC的边
            edge_key = f"DC_XBXA_DC4-{tenant_id}-HAS_TENANT"
            if edge_key not in self.processed_edges:
                self.graph['edges'].append({
                    'source': 'DC_XBXA_DC4',
                    'target': tenant_id,
                    'type': 'HAS_TENANT'
                })
                self.processed_edges.add(edge_key)
            self.processed_nodes['tenant'].add(tenant_id)

    def process_ne_node(self, row):
        """处理网元节点"""
        ne_name = str(row['网元名称'])
        tenant_name = str(row['租户名称'])
        ne_id = f"NE_{ne_name}"
        tenant_id = f"TENANT_{tenant_name}"
        
        if ne_id not in self.processed_nodes['ne']:
            ne_node = {
                'id': ne_id,
                'type': self.extract_node_type(ne_name, 'NE'),
                'level': self.node_levels['NE'],
                'properties': {
                    'name': ne_name
                }
            }
            self.graph['nodes'].append(ne_node)
            self.processed_nodes['ne'].add(ne_id)
        
        # 添加与租户的边
        edge_key = f"{tenant_id}-{ne_id}-HAS_NE"
        if edge_key not in self.processed_edges:
            self.graph['edges'].append({
                'source': tenant_id,
                'target': ne_id,
                'type': 'HAS_NE'
            })
            self.processed_edges.add(edge_key)

    def process_vm_node(self, row):
        """处理虚拟机节点"""
        vm_name = str(row['虚拟机名称'])
        ne_name = str(row['网元名称'])
        vm_id = f"VM_{vm_name}"
        ne_id = f"NE_{ne_name}"
        
        if vm_id not in self.processed_nodes['vm']:
            vm_node = {
                'id': vm_id,
                'type': self.extract_node_type(vm_name, 'VM'),
                'level': self.node_levels['VM'],
                'properties': {
                    'name': vm_name,
                    'cpu': row.get('CPU核数', 0),
                    'memory': row.get('内存大小(GB)', 0),
                    'disk': row.get('磁盘大小(GB)', 0)
                }
            }
            self.graph['nodes'].append(vm_node)
            self.processed_nodes['vm'].add(vm_id)
        
        # 添加与网元的边
        edge_key = f"{ne_id}-{vm_id}-HAS_VM"
        if edge_key not in self.processed_edges:
            self.graph['edges'].append({
                'source': ne_id,
                'target': vm_id,
                'type': 'HAS_VM'
            })
            self.processed_edges.add(edge_key)

    def process_host_node(self, row):
        """处理主机节点"""
        host_name = str(row['主机名称'])
        vm_name = str(row['虚拟机名称'])
        host_id = f"HOST_{host_name}"
        vm_id = f"VM_{vm_name}"
        
        if host_id not in self.processed_nodes['host']:
            host_node = {
                'id': host_id,
                'type': self.extract_node_type(host_name, 'HOST'),
                'level': self.node_levels['HOST'],
                'properties': {
                    'name': host_name,
                    'total_cpu': row.get('主机CPU总核数', 0),
                    'total_memory': row.get('主机内存总量(GB)', 0)
                }
            }
            self.graph['nodes'].append(host_node)
            self.processed_nodes['host'].add(host_id)
        
        # 添加虚拟机到主机的部署关系
        edge_key = f"{vm_id}-{host_id}-DEPLOYED_ON"
        if edge_key not in self.processed_edges:
            self.graph['edges'].append({
                'source': vm_id,
                'target': host_id,
                'type': 'DEPLOYED_ON'
            })
            self.processed_edges.add(edge_key)

    def process_hostgroup_node(self, row):
        """处理主机组节点"""
        hostgroup_name = str(row['主机组名称'])
        host_name = str(row['主机名称'])
        hostgroup_id = f"HOSTGROUP_{hostgroup_name}"
        host_id = f"HOST_{host_name}"
        
        if hostgroup_id not in self.processed_nodes['hostgroup']:
            hostgroup_node = {
                'id': hostgroup_id,
                'type': self.extract_node_type(hostgroup_name, 'HOSTGROUP'),
                'level': self.node_levels['HOSTGROUP'],
                'properties': {
                    'name': hostgroup_name
                }
            }
            self.graph['nodes'].append(hostgroup_node)
            self.processed_nodes['hostgroup'].add(hostgroup_id)
        
        # 添加主机到主机组的归属关系
        edge_key = f"{host_id}-{hostgroup_id}-BELONGS_TO"
        if edge_key not in self.processed_edges:
            self.graph['edges'].append({
                'source': host_id,
                'target': hostgroup_id,
                'type': 'BELONGS_TO'
            })
            self.processed_edges.add(edge_key)

    def process_storagepool_node(self, row):
        """处理存储池节点"""
        storagepool_name = str(row['存储池名称'])
        hostgroup_name = str(row['主机组名称'])
        storagepool_id = f"STORAGEPOOL_{storagepool_name}"
        hostgroup_id = f"HOSTGROUP_{hostgroup_name}"
        
        if storagepool_id not in self.processed_nodes['storagepool']:
            storagepool_node = {
                'id': storagepool_id,
                'type': self.extract_node_type(storagepool_name, 'STORAGEPOOL'),
                'level': self.node_levels['STORAGEPOOL'],
                'properties': {
                    'name': storagepool_name,
                    'total_capacity': row.get('存储池容量(GB)', 0),
                    'used_capacity': row.get('存储池已用容量(GB)', 0)
                }
            }
            self.graph['nodes'].append(storagepool_node)
            self.processed_nodes['storagepool'].add(storagepool_id)
        
        # 添加与主机组的关系
        edge_key = f"{hostgroup_id}-{storagepool_id}-HAS_STORAGE"
        if edge_key not in self.processed_edges:
            self.graph['edges'].append({
                'source': hostgroup_id,
                'target': storagepool_id,
                'type': 'HAS_STORAGE'
            })
            self.processed_edges.add(edge_key)

    def convert(self):
        """执行转换流程"""
        self.load_data()
        self.process_nodes()
        return self.graph

    def save_to_json(self, output_path: str = "datasets/processed/topology_graph.json"):
        """保存为JSON文件"""
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        graph = self.convert()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)
        print(f"已保存图数据到: {output_path}")
        print(f"节点总数: {len(graph['nodes'])}")
        print(f"边总数: {len(graph['edges'])}")
        
        # 打印各类型节点统计
        node_types = {}
        for node in graph['nodes']:
            node_type = node['type']
            node_types[node_type] = node_types.get(node_type, 0) + 1
        print("\n各类型节点统计:")
        for node_type, count in node_types.items():
            print(f"{node_type}: {count}")

if __name__ == "__main__":
    converter = TopologyConverter()
    converter.save_to_json()
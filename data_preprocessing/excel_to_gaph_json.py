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
        # 定义节点类型描述
        self.node_descriptions = {
            'DC': {
                'name': '数据中心',
                'description': '物理数据中心，是所有IT资源的顶层容器'
            },
            'TENANT': {
                'name': '租户',
                'description': '数据中心中的逻辑隔离单元，拥有独立的资源配额和网络元素'
            },
            'NE': {
                'name': '网元',
                'description': '网络功能虚拟化(NFV)部署的功能单元，如AMF、SMF等5G核心网功能'
            },
            'VM': {
                'name': '虚拟机',
                'description': '承载网元功能的虚拟计算资源，由虚拟CPU、内存和存储组成'
            },
            'HOST': {
                'name': '物理主机',
                'description': '提供计算资源的物理服务器，用于运行虚拟机'
            },
            'HOSTGROUP': {
                'name': '主机组',
                'description': '物理主机的逻辑分组，通常基于硬件配置、位置或用途进行分组'
            },
            'TRU': {
                'name': '存储池',
                'description': '提供持久化存储资源的逻辑单元，为虚拟机提供存储空间'
            }
        }
        # 定义边类型描述
        self.edge_descriptions = {
            'HAS_TENANT': {
                'name': '拥有租户',
                'description': '表示数据中心拥有或管理某个租户，这是资源分配的第一层级关系'
            },
            'HAS_NE': {
                'name': '拥有网元',
                'description': '表示某个租户拥有或管理特定的网络元素'
            },
            'HAS_VM': {
                'name': '拥有虚拟机',
                'description': '表示网络元素通过一个或多个虚拟机来实现其功能'
            },
            'DEPLOYED_ON': {
                'name': '部署于',
                'description': '表示虚拟机部署或运行在特定的物理主机上'
            },
            'BELONGS_TO': {
                'name': '属于',
                'description': '表示物理主机属于特定的主机组集合'
            },
            'HAS_STORAGE': {
                'name': '拥有存储',
                'description': '表示主机组关联或使用特定的存储池资源'
            }
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
        """提取节点类型，使用通用类型标识"""
        if base_type == 'TENANT':
            return 'TENANT'
        elif base_type == 'NE':
            return 'NE'
        elif base_type == 'VM':
            return 'VM'
        elif base_type == 'HOST':
            return 'HOST'
        elif base_type == 'HOSTGROUP':
            return 'HOSTGROUP'
        elif base_type == 'STORAGEPOOL':
            return 'TRU'
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
        node_type = 'DC'
        dc_node = {
            'id': 'DC_XBXA_DC4',
            'type': node_type,
            'level': self.node_levels[node_type],
            'properties': {
                'name': 'XBXA_DC4',
                'chinese_name': self.node_descriptions[node_type]['name'],
                'description': self.node_descriptions[node_type]['description']
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
            # 添加配额属性
            tenant_vcpu = row['租户vCPU核数'] if '租户vCPU核数' in row and pd.notna(row['租户vCPU核数']) else 0
            tenant_vmem = row['租户vMEM大小'] if '租户vMEM大小' in row and pd.notna(row['租户vMEM大小']) else 0
            tenant_vdisk = row['租户vDISK大小'] if '租户vDISK大小' in row and pd.notna(row['租户vDISK大小']) else 0
            
            node_type = self.extract_node_type(tenant_name, 'TENANT')
            tenant_node = {
                'id': tenant_id,
                'type': node_type,
                'level': self.node_levels['TENANT'],
                'properties': {
                    'name': tenant_name,
                    'chinese_name': self.node_descriptions['TENANT']['name'],
                    'description': self.node_descriptions['TENANT']['description'],
                    'vcpu': tenant_vcpu,
                    'vmem': tenant_vmem,
                    'vdisk': tenant_vdisk
                }
            }
            self.graph['nodes'].append(tenant_node)
            # 添加与DC的边
            edge_key = f"DC_XBXA_DC4-{tenant_id}-HAS_TENANT"
            if edge_key not in self.processed_edges:
                edge_type = 'HAS_TENANT'
                self.graph['edges'].append({
                    'source': 'DC_XBXA_DC4',
                    'target': tenant_id,
                    'type': edge_type,
                    'properties': {
                        'chinese_name': self.edge_descriptions[edge_type]['name'],
                        'description': self.edge_descriptions[edge_type]['description']
                    }
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
            # 添加配额属性
            ne_vcpu = row['网元vCPU核数'] if '网元vCPU核数' in row and pd.notna(row['网元vCPU核数']) else 0
            ne_vmem = row['网元vMEM大小'] if '网元vMEM大小' in row and pd.notna(row['网元vMEM大小']) else 0
            ne_vdisk = row['网元vDISK大小'] if '网元vDISK大小' in row and pd.notna(row['网元vDISK大小']) else 0
            
            node_type = self.extract_node_type(ne_name, 'NE')
            ne_node = {
                'id': ne_id,
                'type': node_type,
                'level': self.node_levels['NE'],
                'properties': {
                    'name': ne_name,
                    'chinese_name': self.node_descriptions['NE']['name'],
                    'description': self.node_descriptions['NE']['description'],
                    'vcpu': ne_vcpu,
                    'vmem': ne_vmem,
                    'vdisk': ne_vdisk
                }
            }
            self.graph['nodes'].append(ne_node)
            self.processed_nodes['ne'].add(ne_id)
        
        # 添加与租户的边
        edge_key = f"{tenant_id}-{ne_id}-HAS_NE"
        if edge_key not in self.processed_edges:
            edge_type = 'HAS_NE'
            self.graph['edges'].append({
                'source': tenant_id,
                'target': ne_id,
                'type': edge_type,
                'properties': {
                    'chinese_name': self.edge_descriptions[edge_type]['name'],
                    'description': self.edge_descriptions[edge_type]['description']
                }
            })
            self.processed_edges.add(edge_key)

    def process_vm_node(self, row):
        """处理虚拟机节点"""
        vm_name = str(row['虚拟机名称'])
        ne_name = str(row['网元名称'])
        vm_id = f"VM_{vm_name}"
        ne_id = f"NE_{ne_name}"
        
        if vm_id not in self.processed_nodes['vm']:
            # 添加配额属性
            vm_vcpu = row['虚拟机vCPU核数'] if '虚拟机vCPU核数' in row and pd.notna(row['虚拟机vCPU核数']) else 0
            vm_vmem = row['虚拟机vMEM大小'] if '虚拟机vMEM大小' in row and pd.notna(row['虚拟机vMEM大小']) else 0
            vm_vdisk = row['虚拟机vDISK大小'] if '虚拟机vDISK大小' in row and pd.notna(row['虚拟机vDISK大小']) else 0
            
            node_type = self.extract_node_type(vm_name, 'VM')
            vm_node = {
                'id': vm_id,
                'type': node_type,
                'level': self.node_levels['VM'],
                'properties': {
                    'name': vm_name,
                    'chinese_name': self.node_descriptions['VM']['name'],
                    'description': self.node_descriptions['VM']['description'],
                    'vcpu': vm_vcpu,
                    'vmem': vm_vmem,
                    'vdisk': vm_vdisk
                }
            }
            self.graph['nodes'].append(vm_node)
            self.processed_nodes['vm'].add(vm_id)
        
        # 添加与网元的边
        edge_key = f"{ne_id}-{vm_id}-HAS_VM"
        if edge_key not in self.processed_edges:
            edge_type = 'HAS_VM'
            self.graph['edges'].append({
                'source': ne_id,
                'target': vm_id,
                'type': edge_type,
                'properties': {
                    'chinese_name': self.edge_descriptions[edge_type]['name'],
                    'description': self.edge_descriptions[edge_type]['description']
                }
            })
            self.processed_edges.add(edge_key)

    def process_host_node(self, row):
        """处理主机节点"""
        host_name = str(row['主机名称'])
        vm_name = str(row['虚拟机名称'])
        host_id = f"HOST_{host_name}"
        vm_id = f"VM_{vm_name}"
        
        if host_id not in self.processed_nodes['host']:
            # 添加配额属性
            host_cpu = row['主机CPU核数'] if '主机CPU核数' in row and pd.notna(row['主机CPU核数']) else 0
            host_allocated_cpu = row['主机已分配CPU核数'] if '主机已分配CPU核数' in row and pd.notna(row['主机已分配CPU核数']) else 0
            host_mem = row['主机内存大小'] if '主机内存大小' in row and pd.notna(row['主机内存大小']) else 0
            host_allocated_mem = row['主机已分配内存大小'] if '主机已分配内存大小' in row and pd.notna(row['主机已分配内存大小']) else 0
            
            node_type = self.extract_node_type(host_name, 'HOST')
            host_node = {
                'id': host_id,
                'type': node_type,
                'level': self.node_levels['HOST'],
                'properties': {
                    'name': host_name,
                    'chinese_name': self.node_descriptions['HOST']['name'],
                    'description': self.node_descriptions['HOST']['description'],
                    'cpu': host_cpu,
                    'allocated_cpu': host_allocated_cpu,
                    'mem': host_mem,
                    'allocated_mem': host_allocated_mem
                }
            }
            self.graph['nodes'].append(host_node)
            self.processed_nodes['host'].add(host_id)
        
        # 添加虚拟机到主机的部署关系
        edge_key = f"{vm_id}-{host_id}-DEPLOYED_ON"
        if edge_key not in self.processed_edges:
            edge_type = 'DEPLOYED_ON'
            self.graph['edges'].append({
                'source': vm_id,
                'target': host_id,
                'type': edge_type,
                'properties': {
                    'chinese_name': self.edge_descriptions[edge_type]['name'],
                    'description': self.edge_descriptions[edge_type]['description']
                }
            })
            self.processed_edges.add(edge_key)

    def process_hostgroup_node(self, row):
        """处理主机组节点"""
        hostgroup_name = str(row['主机组名称'])
        host_name = str(row['主机名称'])
        hostgroup_id = f"HOSTGROUP_{hostgroup_name}"
        host_id = f"HOST_{host_name}"
        
        if hostgroup_id not in self.processed_nodes['hostgroup']:
            # 添加配额属性
            hostgroup_cpu = row['主机组CPU核数'] if '主机组CPU核数' in row and pd.notna(row['主机组CPU核数']) else 0
            hostgroup_allocated_cpu = row['主机组已分配CPU核数'] if '主机组已分配CPU核数' in row and pd.notna(row['主机组已分配CPU核数']) else 0
            hostgroup_mem = row['主机组内存大小'] if '主机组内存大小' in row and pd.notna(row['主机组内存大小']) else 0
            hostgroup_allocated_mem = row['主机组已分配内存大小'] if '主机组已分配内存大小' in row and pd.notna(row['主机组已分配内存大小']) else 0
            
            node_type = self.extract_node_type(hostgroup_name, 'HOSTGROUP')
            hostgroup_node = {
                'id': hostgroup_id,
                'type': node_type,
                'level': self.node_levels['HOSTGROUP'],
                'properties': {
                    'name': hostgroup_name,
                    'chinese_name': self.node_descriptions['HOSTGROUP']['name'],
                    'description': self.node_descriptions['HOSTGROUP']['description'],
                    'cpu': hostgroup_cpu,
                    'allocated_cpu': hostgroup_allocated_cpu,
                    'mem': hostgroup_mem,
                    'allocated_mem': hostgroup_allocated_mem
                }
            }
            self.graph['nodes'].append(hostgroup_node)
            self.processed_nodes['hostgroup'].add(hostgroup_id)
        
        # 添加主机到主机组的归属关系
        edge_key = f"{host_id}-{hostgroup_id}-BELONGS_TO"
        if edge_key not in self.processed_edges:
            edge_type = 'BELONGS_TO'
            self.graph['edges'].append({
                'source': host_id,
                'target': hostgroup_id,
                'type': edge_type,
                'properties': {
                    'chinese_name': self.edge_descriptions[edge_type]['name'],
                    'description': self.edge_descriptions[edge_type]['description']
                }
            })
            self.processed_edges.add(edge_key)

    def process_storagepool_node(self, row):
        """处理存储池节点"""
        storagepool_name = str(row['存储池名称'])
        hostgroup_name = str(row['主机组名称'])
        storagepool_id = f"STORAGEPOOL_{storagepool_name}"
        hostgroup_id = f"HOSTGROUP_{hostgroup_name}"
        
        if storagepool_id not in self.processed_nodes['storagepool']:
            # 添加配额属性
            storage_size = row['存储空间大小'] if '存储空间大小' in row and pd.notna(row['存储空间大小']) else 0
            allocated_storage = row['已分配存储大小'] if '已分配存储大小' in row and pd.notna(row['已分配存储大小']) else 0
            
            node_type = self.extract_node_type(storagepool_name, 'STORAGEPOOL')
            storagepool_node = {
                'id': storagepool_id,
                'type': node_type,
                'level': self.node_levels['STORAGEPOOL'],
                'properties': {
                    'name': storagepool_name,
                    'chinese_name': self.node_descriptions['TRU']['name'],
                    'description': self.node_descriptions['TRU']['description'],
                    'storage_size': storage_size,
                    'allocated_storage': allocated_storage
                }
            }
            self.graph['nodes'].append(storagepool_node)
            self.processed_nodes['storagepool'].add(storagepool_id)
        
        # 添加与主机组的关系
        edge_key = f"{hostgroup_id}-{storagepool_id}-HAS_STORAGE"
        if edge_key not in self.processed_edges:
            edge_type = 'HAS_STORAGE'
            self.graph['edges'].append({
                'source': hostgroup_id,
                'target': storagepool_id,
                'type': edge_type,
                'properties': {
                    'chinese_name': self.edge_descriptions[edge_type]['name'],
                    'description': self.edge_descriptions[edge_type]['description']
                }
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
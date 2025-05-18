from sqlalchemy import MetaData, Table, Column, Integer, String, Float, DateTime, Text
from datetime import datetime
import pandas as pd

class DynamicTableManager:
    def __init__(self, db):
        self.db = db
        self.metadata = MetaData()
    
    def create_table_from_excel(self, file, base_name):
        """从Excel创建动态表"""
        try:
            # 读取Excel表头
            df = pd.read_excel(file)
            columns = df.columns.tolist()
            
            # 生成表名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            table_name = f"{base_name}_{timestamp}"
            
            # 创建表结构
            table_columns = [
                Column('id', Integer, primary_key=True),
                Column('created_at', DateTime, default=datetime.utcnow)
            ]
            
            # 根据Excel表头创建列
            for col in columns:
                # 获取列的数据类型
                sample_data = df[col].iloc[0] if not df.empty else None
                col_type = self._get_column_type(sample_data)
                table_columns.append(Column(col, col_type))
            
            # 创建表
            table = Table(table_name, self.metadata, *table_columns)
            self.metadata.create_all(self.db.engine)
            
            return table_name
            
        except Exception as e:
            raise Exception(f"创建动态表失败: {str(e)}")
    
    def _get_column_type(self, sample_value):
        """根据样本值确定列类型"""
        if pd.isna(sample_value):
            return Text
        
        if isinstance(sample_value, (int, float)):
            return Float
        
        return Text
    
    def import_data(self, table_name, df):
        """导入数据到动态表"""
        try:
            # 获取表对象
            table = Table(table_name, self.metadata, autoload_with=self.db.engine)
            
            # 转换数据为字典列表
            data = df.to_dict('records')
            
            # 插入数据
            with self.db.engine.connect() as conn:
                conn.execute(table.insert(), data)
                conn.commit()
                
        except Exception as e:
            raise Exception(f"导入数据失败: {str(e)}")
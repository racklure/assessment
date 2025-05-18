from app import create_app, db
from app.models.user import User

def init_admin():
    app = create_app()
    with app.app_context():
        # 检查是否已存在管理员账户
        admin = User.query.filter_by(role='admin').first()
        if admin:
            print("管理员账户已存在，无需重新创建")
            return
        
        # 创建新的管理员账户
        admin = User(
            username='admin',
            name='系统管理员',
            role='admin'
        )
        admin.set_password('admin123')  # 设置初始密码
        
        db.session.add(admin)
        db.session.commit()
        print("管理员账户创建成功！")
        print("用户名: admin")
        print("密码: admin123")
        print("请登录后立即修改密码！")

if __name__ == '__main__':
    init_admin()
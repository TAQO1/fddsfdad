from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from datetime import datetime
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Base, Member, Trainer, Admin, FitnessGoal, HealthMetric, Room, Class, PTSession, ClassEnrollment

DB_NAME = "fitness_club"
DB_USER = "postgres"
DB_PASSWORD = "123456"
DB_HOST = "localhost"
DB_PORT = "5432"


def get_engine():
    global DB_PASSWORD
    if DB_PASSWORD == "":
        DB_PASSWORD = getpass.getpass("PostgreSQL password: ")
    
    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(connection_string)


def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def drop_all_tables():
    engine = get_engine()
    print("WARNING: dropping all database tables...")
    confirm = input("Are you sure you want to delete all tables? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Operation cancelled.")
        return False
    
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            try:
                conn.execute(text("DROP INDEX IF EXISTS idx_ptsession_trainer_time CASCADE"))
                conn.commit()
            except Exception:
                pass

        Base.metadata.drop_all(engine)
        print("All tables and indexes dropped successfully.")
        return True
    except Exception as e:
        print(f"Error dropping tables: {e}")
        return False


def create_view_and_trigger(engine):
    from sqlalchemy import text
    
    with engine.connect() as conn:
        view_sql = """
        CREATE OR REPLACE VIEW MemberHealthSummary AS
        SELECT
            m.member_id,
            m.name AS member_name,
            m.email,
            hm.metric_type,
            hm.metric_value,
            hm.timestamp AS last_metric_time
        FROM Member m
        LEFT JOIN LATERAL (
            SELECT *
            FROM HealthMetric h
            WHERE h.member_id = m.member_id
            ORDER BY h.timestamp DESC
            LIMIT 1
        ) hm ON TRUE;
        """
        
        try:
            conn.execute(text(view_sql))
            conn.commit()
            print("Database view 'MemberHealthSummary' created successfully.")
        except Exception as e:
            if "already exists" not in str(e).lower():
                print(f"View creation error: {e}")

        trigger_function_sql = """
        CREATE OR REPLACE FUNCTION check_class_capacity()
        RETURNS TRIGGER AS $$
        DECLARE
            room_capacity INT;
        BEGIN
            SELECT capacity INTO room_capacity
            FROM Room
            WHERE room_id = NEW.room_id;
            
            IF NEW.capacity > room_capacity THEN
                RAISE EXCEPTION 'Class capacity (%) cannot exceed room capacity (%)', NEW.capacity, room_capacity;
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
        
        try:
            conn.execute(text(trigger_function_sql))
            conn.commit()
        except Exception:
            pass

        trigger_sql = """
        DROP TRIGGER IF EXISTS trg_check_class_capacity ON "Class";
        
        CREATE TRIGGER trg_check_class_capacity
        BEFORE INSERT OR UPDATE ON "Class"
        FOR EACH ROW
        EXECUTE FUNCTION check_class_capacity();
        """
        
        try:
            conn.execute(text(trigger_sql))
            conn.commit()
            print("Database trigger 'trg_check_class_capacity' created successfully.")
        except Exception:
            pass


def create_tables():
    engine = get_engine()
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    required_tables = ['Member', 'Trainer', 'Admin', 'Room', 'Class', 'FitnessGoal', 'HealthMetric', 'PTSession', 'ClassEnrollment']
    missing_tables = [t for t in required_tables if t not in existing_tables]
    
    if missing_tables:
        print("Creating database tables from ORM models...")
        print("Missing tables: " + ", ".join(missing_tables))

        try:
            with engine.connect() as conn:
                conn.execute(text("DROP INDEX IF EXISTS idx_ptsession_trainer_time"))
                conn.commit()
        except Exception:
            pass

        try:
            Base.metadata.create_all(engine, checkfirst=True)
            inspector = inspect(engine)
            new_tables = inspector.get_table_names()
            still_missing = [t for t in required_tables if t not in new_tables]
            
            if not still_missing:
                print("All database tables created successfully.")
            else:
                print(f"Warning: Some tables still missing: {still_missing}")
                raise Exception(f"Failed to create tables: {still_missing}")
        except Exception as e:
            error_str = str(e).lower()
            if "already exists" in error_str or "duplicate" in error_str:
                inspector = inspect(engine)
                new_tables = inspector.get_table_names()
                still_missing = [t for t in required_tables if t not in new_tables]
                if not still_missing:
                    print("Tables created (some indexes or constraints may have been created previously).")
                else:
                    print(f"Warning: Some tables still missing: {still_missing}")
                    raise
            else:
                raise
    else:
        print("All required tables already exist.")

    print("Creating database view and trigger...")
    create_view_and_trigger(engine)


def register_member(session):
    print("\n=== Register New Member ===")
    name = input("Name: ")
    email = input("Email: ")
    dob_str = input("Date of birth (YYYY-MM-DD, optional): ") or None
    gender = input("Gender (optional): ") or None
    phone = input("Phone (optional): ") or None
    
    dob = None
    if dob_str:
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        except ValueError:
            print("Invalid date format. Member registered without date of birth.")
    
    try:
        member = Member(
            name=name,
            email=email,
            date_of_birth=dob,
            gender=gender,
            phone=phone
        )
        session.add(member)
        session.commit()
        print(f"Member registered with ID: {member.member_id}")
    except IntegrityError as e:
        session.rollback()
        print(f"Error registering member: {str(e)}")
    except Exception as e:
        session.rollback()
        print(f"Unexpected error: {str(e)}")


def update_member_profile(session):
    print("\n=== Update Member Profile ===")
    member_id = int(input("Member ID: "))
    member = session.query(Member).filter(Member.member_id == member_id).first()
    if not member:
        print("Member not found.")
        return

    print("\nCurrent Profile:")
    print(f"  Name: {member.name}")
    print(f"  Email: {member.email}")
    print(f"  Phone: {member.phone if member.phone else '(not set)'}")
    print(f"  Date of Birth: {member.date_of_birth if member.date_of_birth else '(not set)'}")
    print(f"  Gender: {member.gender if member.gender else '(not set)'}")
    
    print("\nLeave field blank to keep current value.")
    name = input(f"New name (current: {member.name}): ").strip() or None
    phone = input(f"New phone (current: {member.phone if member.phone else 'not set'}): ").strip() or None

    if name is not None:
        print(f"  Updating name: '{member.name}' -> '{name}'")
        member.name = name
    if phone is not None:
        print(f"  Updating phone: '{member.phone if member.phone else 'not set'}' -> '{phone}'")
        member.phone = phone
    
    try:
        session.commit()
        print("\nProfile updated successfully!")
    except Exception as e:
        session.rollback()
        print(f"error updating profile: {str(e)}")


def add_health_metric(session):
    print("\n=== Add Health Metric ===")
    member_id = int(input("Member ID: "))
    metric_type = input("Metric type (e.g., 'Weight (kg)'): ")
    metric_value = float(input("Metric value: "))

    member = session.query(Member).filter(Member.member_id == member_id).first()
    if not member:
        print("Member not found.")
        return
    
    try:
        metric = HealthMetric(
            member_id=member_id,
            metric_type=metric_type,
            metric_value=metric_value,
            timestamp=datetime.now()
        )
        session.add(metric)
        session.commit()
        print("Metric recorded.")
    except Exception as e:
        session.rollback()
        print(f"Error recording metric: {str(e)}")


def book_pt_session(session):
    print("\n=== Book PT Session ===")
    try:
        member_id = int(input("Member ID: "))
    except ValueError:
        print("Invalid member ID. Please enter a number.")
        return
    
    try:
        trainer_id = int(input("Trainer ID: "))
    except ValueError:
        print("Invalid trainer ID. Please enter a number.")
        return
    
    session_time_str = input("Session time (YYYY-MM-DD HH:MM): ")
    
    try:
        session_time = datetime.strptime(session_time_str, "%Y-%m-%d %H:%M")
    except ValueError:
        print("Invalid date/time format. Please use YYYY-MM-DD HH:MM")
        return
    
    try:
        pt_session = PTSession(
            member_id=member_id,
            trainer_id=trainer_id,
            session_time=session_time,
            status='scheduled'
        )
        session.add(pt_session)
        session.commit()
        print("Session booked.")
    except IntegrityError as e:
        session.rollback()
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        print(f"Error booking session: {error_msg}")
    except Exception as e:
        session.rollback()
        print(f"Unexpected error: {str(e)}")


def view_available_classes(session):
    print("\n=== Available Classes ===")
    
    classes = session.query(Class).join(Room).join(Trainer).order_by(Class.class_time).all()
    
    if not classes:
        print("No classes available.")
        return
    
    print(f"\n{'ID':<6} {'Class Name':<25} {'Time':<20} {'Trainer':<20} {'Room':<15} {'Enrolled':<10} {'Capacity':<10}")
    print("-" * 110)
    
    for class_obj in classes:
        # Count current enrollments
        enrollment_count = session.query(ClassEnrollment).filter(
            ClassEnrollment.class_id == class_obj.class_id
        ).count()
        
        spaces_available = class_obj.capacity - enrollment_count
        status = "FULL" if spaces_available == 0 else f"{spaces_available} spots"
        
        print(
            f"{class_obj.class_id:<6} "
            f"{class_obj.class_name[:24]:<25} "
            f"{str(class_obj.class_time):<20} "
            f"{class_obj.trainer.name[:19]:<20} "
            f"{class_obj.room.name[:14]:<15} "
            f"{enrollment_count}/{class_obj.capacity:<10} "
            f"{status:<10}"
        )


def signup_for_class(session):
    print("\n=== Sign Up for Class ===")
    
    try:
        member_id = int(input("Member ID: "))
    except ValueError:
        print("Invalid member ID. Please enter a number.")
        return
    
    member = session.query(Member).filter(Member.member_id == member_id).first()
    if not member:
        print("Member not found.")
        return
    
    view_available_classes(session)
    
    try:
        class_id = int(input("\nEnter Class ID to enroll: "))
    except ValueError:
        print("Invalid class ID. Please enter a number.")
        return
    
    class_obj = session.query(Class).filter(Class.class_id == class_id).first()
    if not class_obj:
        print("Class not found.")
        return
    
    existing_enrollment = session.query(ClassEnrollment).filter(
        ClassEnrollment.member_id == member_id,
        ClassEnrollment.class_id == class_id
    ).first()
    
    if existing_enrollment:
        print(f"You are already enrolled in this class.")
        return
    
    enrollment_count = session.query(ClassEnrollment).filter(
        ClassEnrollment.class_id == class_id
    ).count()
    
    if enrollment_count >= class_obj.capacity:
        print(f"Class is full. Capacity: {class_obj.capacity}, Enrolled: {enrollment_count}")
        return
    
    try:
        enrollment = ClassEnrollment(
            member_id=member_id,
            class_id=class_id,
            enrollment_date=datetime.now()
        )
        session.add(enrollment)
        session.commit()
        
        spaces_remaining = class_obj.capacity - enrollment_count - 1
        print(f"\n Successfully enrolled in '{class_obj.class_name}'!")
        print(f"  Class time: {class_obj.class_time}")
        print(f"  Trainer: {class_obj.trainer.name}")
        print(f"  Room: {class_obj.room.name}")
        print(f"  Spaces remaining: {spaces_remaining}")
    except IntegrityError as e:
        session.rollback()
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        print(f"Error enrolling in class: {error_msg}")
    except Exception as e:
        session.rollback()
        print(f"Unexpected error: {str(e)}")


def view_trainer_schedule(session):
    print("\n=== Trainer Schedule ===")
    trainer_id = int(input("Trainer ID: "))
    
    trainer = session.query(Trainer).filter(Trainer.trainer_id == trainer_id).first()
    if not trainer:
        print("Trainer not found.")
        return
    
    print("\n-- PT Sessions --")
    pt_sessions = session.query(PTSession).join(Member).filter(
        PTSession.trainer_id == trainer_id
    ).order_by(PTSession.session_time).all()
    
    if pt_sessions:
        for pt_session in pt_sessions:
            print(
                f"Session {pt_session.session_id} | {pt_session.session_time} | "
                f"Member: {pt_session.member.name} | Status: {pt_session.status}"
            )
    else:
        print("No PT sessions scheduled.")
    
    print("\n-- Classes --")
    classes = session.query(Class).join(Room).filter(
        Class.trainer_id == trainer_id
    ).order_by(Class.class_time).all()
    
    if classes:
        for class_obj in classes:
            print(
                f"Class {class_obj.class_id} | {class_obj.class_time} | "
                f"{class_obj.class_name} @ {class_obj.room.name}"
            )
    else:
        print("No classes scheduled.")


def member_lookup(session):
    print("\n=== Member Lookup (Trainer) ===")
    name_like = input("Search name (partial allowed): ")
    
    members = session.query(Member).filter(
        func.lower(Member.name).like(f"%{name_like.lower()}%")
    ).all()
    
    if not members:
        print("No members found.")
        return
    
    for member in members:
        print(f"{member.member_id}: {member.name} ({member.email})")
    
    member_id = int(input("Enter Member ID to view details: "))
    
    member = session.query(Member).filter(Member.member_id == member_id).first()
    if not member:
        print("Member not found.")
        return
    
    latest_metric = session.query(HealthMetric).filter(
        HealthMetric.member_id == member_id
    ).order_by(HealthMetric.timestamp.desc()).first()
    
    goals = session.query(FitnessGoal).filter(
        FitnessGoal.member_id == member_id
    ).all()
    
    print("\n-- Latest Metric --")
    if latest_metric:
        print(
            f"{latest_metric.metric_type}: {latest_metric.metric_value} "
            f"({latest_metric.timestamp})"
        )
    else:
        print("No metrics recorded.")
    
    print("\n-- Goals --")
    if goals:
        for goal in goals:
            print(
                f"{goal.goal_type} target {goal.target_value} "
                f"({goal.start_date} -> {goal.end_date})"
            )
    else:
        print("No goals defined.")


def create_trainer(session):
    print("\n=== Create Trainer ===")
    name = input("Trainer name: ")
    email = input("Email: ")
    specialization = input("Specialization (optional): ") or None
    
    try:
        trainer = Trainer(
            name=name,
            email=email,
            specialization=specialization
        )
        session.add(trainer)
        session.commit()
        print(f"Trainer created with ID: {trainer.trainer_id}")
    except IntegrityError as e:
        session.rollback()
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        if "email" in error_msg.lower() or "unique" in error_msg.lower():
            print(f"Error: Email '{email}' is already registered. Please use a different email.")
        else:
            print(f"Error creating trainer: {error_msg}")
    except Exception as e:
        session.rollback()
        print(f"Error creating trainer: {str(e)}")


def create_room(session):
    print("\n=== Create Room ===")
    name = input("Room name: ")
    capacity = int(input("Capacity: "))
    
    try:
        room = Room(name=name, capacity=capacity)
        session.add(room)
        session.commit()
        print(f"Room created with ID: {room.room_id}")
    except IntegrityError as e:
        session.rollback()
        print(f"Error creating room: Room name may already exist. {str(e)}")
    except Exception as e:
        session.rollback()
        print(f"Error creating room: {str(e)}")


def create_class(session):
    print("\n=== Create Class ===")
    trainer_id = int(input("Trainer ID: "))
    room_id = int(input("Room ID: "))
    class_name = input("Class name: ")
    class_time_str = input("Class time (YYYY-MM-DD HH:MM): ")
    capacity = int(input("Capacity: "))
    
    try:
        class_time = datetime.strptime(class_time_str, "%Y-%m-%d %H:%M")
    except ValueError:
        print("Invalid date/time format. Please use YYYY-MM-DD HH:MM")
        return
    
    try:
        class_obj = Class(
            trainer_id=trainer_id,
            room_id=room_id,
            class_name=class_name,
            class_time=class_time,
            capacity=capacity
        )
        session.add(class_obj)
        session.commit()
        print("Class created.")
    except IntegrityError as e:
        session.rollback()
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        print(f"Error creating class: {error_msg}")
    except Exception as e:
        session.rollback()
        print(f"Unexpected error: {str(e)}")


def member_menu(session):
    while True:
        print("\n--- Member Menu ---")
        print("1. Register Member")
        print("2. Update Member Profile")
        print("3. Add Health Metric")
        print("4. Book PT Session")
        print("5. View Available Classes")
        print("6. Sign Up for Class")
        print("0. Back")
        choice = input("Choice: ")
        if choice == "1":
            register_member(session)
        elif choice == "2":
            update_member_profile(session)
        elif choice == "3":
            add_health_metric(session)
        elif choice == "4":
            book_pt_session(session)
        elif choice == "5":
            view_available_classes(session)
        elif choice == "6":
            signup_for_class(session)
        elif choice == "0":
            break
        else:
            print("Invalid choice.")


def trainer_menu(session):
    while True:
        print("\n--- Trainer Menu ---")
        print("1. View Schedule")
        print("2. Member Lookup")
        print("0. Back")
        choice = input("Choice: ")
        if choice == "1":
            view_trainer_schedule(session)
        elif choice == "2":
            member_lookup(session)
        elif choice == "0":
            break
        else:
            print("Invalid choice.")


def authenticate_admin(session):
    print("\n=== Admin Authentication ===")
    username = input("Username: ")
    password = input("Password: ")
    
    admin = session.query(Admin).filter(Admin.username == username).first()
    
    if admin and admin.password_hash == password:
        print(f"Authenticated as {admin.name}")
        return admin
    else:
        print("Authentication failed. Invalid username or password.")
        return None


def create_default_admin(session):
    admin = session.query(Admin).filter(Admin.username == 'admin').first()
    if not admin:
        default_admin = Admin(
            username='admin',
            password_hash='admin123',
            name='System Administrator',
            email='admin@fitnessclub.com'
        )
        session.add(default_admin)
        session.commit()
        print("Default admin account created (username: admin, password: admin123).")


def admin_menu(session):
    while True:
        print("\n--- Admin Menu ---")
        print("1. Create Trainer")
        print("2. Create Room")
        print("3. Create Class")
        print("4. Drop All Tables (Reset Database)")
        print("0. Back")
        choice = input("Choice: ")
        if choice == "1":
            create_trainer(session)
        elif choice == "2":
            create_room(session)
        elif choice == "3":
            create_class(session)
        elif choice == "4":
            if drop_all_tables():
                print("\nDatabase reset complete. Restart the application to recreate tables.")
                input("Press Enter to continue...")
                return
        elif choice == "0":
            break
        else:
            print("Invalid choice.")


def main_menu():
    print("\nInitializing database...")
    try:
        create_tables()
    except Exception as e:
        print(f"\nERROR: Could not create database tables!")
        print(f"Error details: {e}")
        print("\nPlease ensure:")
        print("1. PostgreSQL is running")
        print("2. Database 'fitness_club' exists")
        print("3. Database credentials are correct")
        return
    
    session = get_session()
    
    try:
        create_default_admin(session)
    except Exception as e:
        print(f"Note: Could not create default admin: {e}")
    
    try:
        while True:
            print("\n=== Health & Fitness Club Management ===")
            print("1. Member Functions")
            print("2. Trainer Functions")
            print("3. Admin Functions")
            print("0. Exit")
            choice = input("Choice: ")
            if choice == "1":
                member_menu(session)
            elif choice == "2":
                trainer_menu(session)
            elif choice == "3":
                admin = authenticate_admin(session)
                if admin:
                    admin_menu(session)
                else:
                    print("Access denied. Admin authentication required.")
            elif choice == "0":
                break
            else:
                print("Invalid choice.")
    finally:
        session.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--drop-tables":
        drop_all_tables()
        print("\nTables dropped Run the application again to create them fresh.")
    else:
        main_menu()

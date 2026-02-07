
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.task import Task, TaskStatus
from app.models.subtask import Subtask
from app.crud.subtasks import create_subtask, toggle_subtask
from app.crud.task import create_task, delete_task
from app.schemas.task import TaskCreate

async def verify_subtasks():
    async with AsyncSessionLocal() as db:
        print("🚀 Starting Subtasks Verification...")
        
        # 1. Get a test user (User ID 10 from previous logs)
        user = await db.get(User, 10)
        if not user:
            print("❌ Test user (ID 10) not found. Please create a user first.")
            return

        print(f"👤 Using user: {user.email}")
        
        # 2. Create a parent task
        print("\n1️⃣ Creating parent task...")
        task_data = TaskCreate(
            title="Test Parent Task for Subtasks",
            due_date=datetime.now() + timedelta(days=1)
        )
        task = await create_task(db, task_data, user)
        print(f"✅ Parent task created: ID {task.id}")
        
        try:
            # 3. Add subtasks
            print("\n2️⃣ Adding subtasks...")
            s1 = await create_subtask(db, task.id, "Subtask 1")
            s2 = await create_subtask(db, task.id, "Subtask 2")
            print(f"✅ Subtask 1 created: ID {s1.id}")
            print(f"✅ Subtask 2 created: ID {s2.id}")
            
            # 4. Toggle first subtask
            print("\n3️⃣ Toggling Subtask 1...")
            s1 = await toggle_subtask(db, s1)
            print(f"✅ Subtask 1 completed: {s1.is_completed}")
            
            # Verify parent status (should still be PENDING)
            await db.refresh(task)
            print(f"ℹ️ Parent status: {task.status}")
            if task.status != TaskStatus.PENDING:
                 print("❌ Parent task should remain PENDING")
            else:
                 print("✅ Parent task status verified (PENDING)")

            # 5. complete second subtask
            print("\n4️⃣ Toggling Subtask 2 (Final subtask)...")
            s2 = await toggle_subtask(db, s2)
            print(f"✅ Subtask 2 completed: {s2.is_completed}")
            
            # 6. Verify auto-complete
            await db.refresh(task)
            print(f"ℹ️ Parent status: {task.status}")
            if task.status == TaskStatus.COMPLETED:
                print("✅ Parent task AUTO-COMPLETED successfully! 🎉")
            else:
                print(f"❌ Parent task failed to auto-complete. Status: {task.status}")
                
        finally:
            # Cleanup
            print("\n🧹 Cleaning up...")
            await delete_task(db, task)
            await db.commit()
            print("✅ Test data deleted")

if __name__ == "__main__":
    asyncio.run(verify_subtasks())

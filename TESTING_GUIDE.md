# 🧪 AuraTask Frontend Testing Guide

Follow these steps to test every feature. Report any issues and I'll fix them!

---

## 📍 URLs
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs

---

## ✅ Test 1: User Registration

1. Open http://localhost:3000
2. Click **"Register"** or **"Sign Up"**
3. Fill in:
   - Email: `160421737073@mjcollege.ac.in`
   - Password: `Ibrahim@321`
   - Timezone: `Asia/Kolkata`
4. Click Submit

**Expected**: Account created, redirected to login or dashboard

---

## ✅ Test 2: User Login

1. Open http://localhost:3000
2. Enter registered credentials
3. Click **"Login"**

**Expected**: Redirected to dashboard, see empty task list

---

## ✅ Test 3: Create Task with NLP

1. On dashboard, find the task input field
2. Type: `Submit report #Urgent by tomorrow 5pm`
3. Click **Add Task** or press Enter

**Expected**: 
- Task created with title "Submit report"
- Priority: URGENT
- Due date: Tomorrow at 5:00 PM

---

## ✅ Test 4: Create Simple Task

1. Type: `Buy groceries`
2. Submit

**Expected**: Task created with default MEDIUM priority

---

## ✅ Test 5: View Task List

1. Check dashboard after creating tasks

**Expected**: See all your tasks with:
- Title
- Priority badge (color-coded)
- Due date
- Status

---

## ✅ Test 6: Complete a Task

1. Find a task in your list
2. Click the **complete button** (checkmark/checkbox)

**Expected**: Task marked as completed, possibly moved to completed section

---

## ✅ Test 7: Delete a Task

1. Find a task
2. Click **delete button** (trash icon)

**Expected**: Task removed from list

---

## ✅ Test 8: Edit Task (if available)

1. Click on a task to edit
2. Change title or priority
3. Save

**Expected**: Task updated with new values

---

## ✅ Test 9: Snooze Task (if available)

1. Find a task
2. Click **snooze** button
3. Choose duration (e.g., 1 hour)

**Expected**: Task's `snoozed_until` set, notification delayed

---

## ✅ Test 10: Notification Settings

1. Find **Settings** or **Notifications** section
2. Enable Email notifications
3. Enable Telegram notifications
4. Enter Telegram Chat ID: `5800019030`
5. Save

**Expected**: Settings saved successfully

---

## ✅ Test 11: Test Email Notification

Via Swagger (http://localhost:8000/docs):
1. `POST /api/notifications/test`
2. Body: `{"channel": "EMAIL"}`

**Expected**: Email received at `ibrahimaejaz@gmail.com`

---

## ✅ Test 12: Test Telegram Notification

Via Swagger:
1. `POST /api/notifications/test`
2. Body: `{"channel": "TELEGRAM"}`

**Expected**: Telegram message received from your bot

---

## ✅ Test 13: User Logout

1. Find **Logout** button
2. Click it

**Expected**: 
- Redirected to login page
- Cannot access dashboard without logging in again

---

## ✅ Test 14: Protected Routes

1. After logout, try accessing dashboard directly
2. Or try API without token

**Expected**: Redirected to login / 401 Unauthorized

---

## ✅ Test 15: Real-time Updates (WebSocket)

1. Open dashboard in two browser tabs (same user)
2. Create a task in Tab 1

**Expected**: Task appears in Tab 2 without refresh

---

## 📋 Issue Reporting Format

When reporting issues, please include:

```
**Test #**: [number]
**What I did**: [steps]
**Expected**: [what should happen]
**Actual**: [what actually happened]
**Error message**: [if any]
```

---

## 🚀 Ready for Production When:

- [ ] All 15 tests pass
- [ ] No console errors in browser
- [ ] No server errors in terminal

Good luck testing! 🎯

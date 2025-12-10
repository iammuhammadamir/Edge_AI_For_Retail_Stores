# ClientBridge Website Analysis

## Overview

The `ClientBridge` folder contains a **full-stack web application** originally built as a "Gas Station Security Management System" but has been adapted for retail store management. It was developed on **Replit** and appears to be a prototype/demo system.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite, TypeScript, TailwindCSS, shadcn/ui |
| **Backend** | Express.js (Node.js), TypeScript |
| **Database** | PostgreSQL (via Drizzle ORM) |
| **Auth** | Session-based (express-session + connect-pg-simple) |
| **Hosting** | Replit (configured for autoscale deployment) |

---

## Current State

### ✅ What Works
- Full authentication system (login/logout with session management)
- Role-based access control (owner, manager, reviewer)
- Multi-location support
- Video clip upload and viewing
- Customer management (CRUD operations)
- Inventory management
- Notification system
- Camera management (RTSP URLs stored in DB)
- Review workflow for flagging suspicious activity

### ⚠️ What's Missing / Mocked
- **Facial recognition is MOCKED** - The critical integration point:
  ```typescript
  // server/routes.ts line 254-256
  // TODO: Integrate facial recognition here
  // For now, we'll simulate face detection with mock data
  const mockFaceId = `face-${nanoid(6)}`;
  ```
- No actual face detection or embedding extraction
- Customer `faceId` is randomly generated, not from real recognition
- No connection to edge devices (Jetson)

---

## Database Schema

| Table | Purpose |
|-------|---------|
| `locations` | Store locations (multi-tenant) |
| `cameras` | Camera info with RTSP URLs |
| `users` | Auth with roles (owner/manager/reviewer) |
| `video_clips` | Uploaded video clips |
| `customers` | Customer profiles with `faceId` |
| `reviews` | Manager review decisions |
| `inventory_items` | Store inventory |
| `notifications` | System notifications |

### Key Fields for Integration
```typescript
// customers table
faceId: text("face_id").notNull().unique()  // <-- This needs real embeddings
photoUrl: text("photo_url")                  // <-- Face image URL
points: integer("points")                    // Loyalty points
flag: text("flag")                           // red/yellow/green
```

---

## Deployment Status

### Replit Configuration (`.replit`)
- Configured for **autoscale deployment**
- Build: `npm run build`
- Run: `npm run start`
- Port 5000 (backend) → external port 80

### Environment Variables Required
```
DATABASE_URL          # PostgreSQL connection string
SESSION_SECRET        # Session encryption key
RECAPTCHA_SECRET_KEY  # Google reCAPTCHA (optional)
RECAPTCHA_SITE_KEY    # Google reCAPTCHA (optional)
```

### Unknown Deployment State
- No evidence of current live deployment URL
- Replit projects can be deployed but unclear if this one is active
- Would need to check Replit dashboard

---

## Security Features

### Implemented
- Session-based authentication with PostgreSQL store
- Role-based access control (owner/manager/reviewer)
- Location-based data isolation (managers only see their location)
- CAPTCHA after failed login attempts
- IP-based rate limiting for login
- Session regeneration on login (prevents fixation)

### Concerns
- **Passwords stored in plain text** (no hashing!)
  ```typescript
  // routes.ts line 172
  if (!user || user.password !== password) {
  ```
- Default users with weak passwords (manager1/manager1, owner/owner123)
- No HTTPS enforcement in code (relies on Replit proxy)

---

## Features That May Be Unnecessary

### For Visitor Counter Use Case
| Feature | Relevance |
|---------|-----------|
| Video clip upload | ❌ Not needed - edge device captures |
| Inventory management | ❌ Not needed for visitor counting |
| YOLO training pipeline | ❌ Mentioned in README but not implemented |
| Bounding box annotations | ❌ Not needed |
| Review workflow | ⚠️ Maybe useful for flagged customers |
| reCAPTCHA | ⚠️ Nice to have but not critical |

### Potentially Useful
| Feature | Relevance |
|---------|-----------|
| Customer management | ✅ Core - displays visitors |
| Location management | ✅ Multi-store support |
| Notification system | ✅ Alerts for flagged visitors |
| Role-based access | ✅ Owner vs manager views |
| Camera management | ✅ Store camera RTSP URLs |

---

## Integration Points

### Where Edge Device Should Connect

1. **New API Endpoint Needed**: `/api/edge/visitor`
   ```typescript
   // Proposed endpoint for edge device to report visitors
   POST /api/edge/visitor
   {
     "locationId": 1,
     "cameraId": 1,
     "embedding": [0.123, 0.456, ...],  // 512-dim float32
     "imageBase64": "...",               // Best frame
     "timestamp": "2025-12-06T02:00:00Z"
   }
   ```

2. **Backend Should**:
   - Receive embedding from edge device
   - Match against stored embeddings (cosine similarity)
   - Create/update customer record
   - Increment visit count
   - Return visitor info (new/returning, ID, points)

3. **Current Mock Code to Replace** (`server/routes.ts:254-278`):
   ```typescript
   // REPLACE THIS:
   const mockFaceId = `face-${nanoid(6)}`;
   
   // WITH: Real embedding matching logic
   ```

---

## File Structure Summary

```
ClientBridge/
├── client/                 # React frontend
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.tsx   # Main UI (83KB - large file)
│       │   ├── Admin.tsx       # Admin panel
│       │   └── Login.tsx       # Auth page
│       └── components/ui/      # shadcn components
├── server/
│   ├── index.ts           # Express server setup
│   ├── routes.ts          # API endpoints (1129 lines)
│   ├── dbStorage.ts       # Database operations
│   └── storage.ts         # Storage interface
├── shared/
│   └── schema.ts          # Drizzle schema (DB tables)
├── .replit                # Replit deployment config
└── package.json           # Dependencies
```

---

## Recommended Next Steps

### Phase 1: Minimal Integration
1. Add `/api/edge/visitor` endpoint to receive data from Jetson
2. Store embeddings in `customers` table (need to add `embedding` BLOB column)
3. Implement cosine similarity matching in backend
4. Keep existing UI - it already shows customers

### Phase 2: Cleanup
1. Remove unused features (inventory, video upload, YOLO)
2. Hash passwords properly
3. Simplify Dashboard.tsx (currently 83KB / 2344 lines)

### Phase 3: Enhancement
1. Real-time updates via WebSocket
2. Live camera feed display
3. Analytics dashboard for visitor trends

---

## Questions to Resolve

1. **Is this deployed?** Check Replit dashboard for deployment URL
2. **Database access?** Need PostgreSQL connection string
3. **Keep inventory feature?** Or remove for simplicity?
4. **Authentication method for edge device?** API key? JWT?
5. **Embedding storage format?** BLOB in PostgreSQL or separate vector DB?

---

## Summary

The ClientBridge website is a **functional prototype** with good bones but needs:
1. **Real facial recognition integration** (currently mocked)
2. **API endpoint for edge device** communication
3. **Security improvements** (password hashing)
4. **Cleanup of unused features** for clarity

The existing customer management, location support, and notification system are directly usable for the visitor counter use case.

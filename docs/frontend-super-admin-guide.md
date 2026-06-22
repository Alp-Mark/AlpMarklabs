# AlpMark Super Admin Frontend - Complete Implementation Guide

**Version 1.0**  
**Created: 2026-06-21**  
**Persona: Super Admin (AlpMark Platform Administrator)**

---

## Table of Contents

1. [Super Admin Role Overview](#super-admin-role-overview)
2. [Pages Required](#pages-required)
3. [API Endpoints Reference](#api-endpoints-reference)
4. [Data Models](#data-models)
5. [Component Specifications](#component-specifications)
6. [Page Implementations](#page-implementations)
7. [Navigation & Routing](#navigation--routing)
8. [Step-by-Step Build Instructions](#step-by-step-build-instructions)

---

## Super Admin Role Overview

### Who is Super Admin?

**Super Admin** is an **AlpMark employee** (not a customer) who manages the platform itself.

### What Super Admin Can Do

✅ **Create new tenants** (customer organizations)  
✅ **Create the initial Executive Owner** for each tenant  
✅ **View all tenants** with status, subscription, and user counts  
✅ **Suspend or activate tenants**  
✅ **Delete tenants** (⚠️ DESTRUCTIVE - deletes all customer data)  
✅ **Monitor platform health** and system metrics  
✅ **View tenant subscription details** (read-only)  

### What Super Admin CANNOT Do

❌ **Access customer business data** (recommendations, KPIs, simulations)  
❌ **Modify customer subscriptions** (customers manage their own billing)  
❌ **Log in as a customer user**  
❌ **View customer dashboards**  

### Authentication

Super Admin logs in just like any other user:
- Email: `admin@alpmark.com` (or similar)
- Password: Set during account creation
- JWT token with `platform_role: "super_admin"`

---

## Pages Required

Super Admin has **3 primary pages**:

### Page 1: Tenant Management (`/platform/tenants`)
- **Purpose**: List all tenants, create new tenants, manage tenant status
- **URL**: `/platform/tenants`
- **Components**: TenantTable, CreateTenantModal, TenantStatusBadge

### Page 2: Tenant Details (`/platform/tenants/:tenant_id`)
- **Purpose**: View single tenant details, subscription info, user list
- **URL**: `/platform/tenants/{tenant_id}`
- **Components**: TenantDetailsCard, UserListTable, SubscriptionCard

### Page 3: System Health (`/platform/health`)
- **Purpose**: Monitor platform health, integration status, error logs
- **URL**: `/platform/health`
- **Components**: HealthStatusCard, MetricsChart, ErrorLogTable

---

## API Endpoints Reference

### Base URL
```
https://alpmark-production.up.railway.app
```

### Authentication Header
All endpoints require JWT token:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Endpoint 1: List All Tenants

**Request:**
```http
GET /admin/tenants?skip=0&limit=50
Authorization: Bearer <token>
```

**Response:** (200 OK)
```json
{
  "tenants": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "One8 Apparel",
      "domain": "one8",
      "status": "active",
      "subscription_plan": "professional",
      "total_users": 5,
      "created_at": "2026-01-15T10:30:00Z",
      "executive_owner_email": "owner@one8.com"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

**Status Enum:**
- `"active"` - Tenant is operational
- `"suspended"` - Tenant is suspended (users cannot log in)
- `"deleted"` - Tenant is soft-deleted

---

### Endpoint 2: Get Tenant Details

**Request:**
```http
GET /admin/tenants/{tenant_id}
Authorization: Bearer <token>
```

**Path Parameter:**
- `tenant_id` (UUID): Tenant ID

**Response:** (200 OK)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "One8 Apparel",
  "domain": "one8",
  "status": "active",
  "subscription_plan": "professional",
  "seat_limit": 10,
  "seats_used": 5,
  "total_users": 5,
  "total_integrations": 3,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-06-20T14:22:00Z",
  "executive_owner_email": "owner@one8.com",
  "subscription": {
    "id": "sub-uuid",
    "plan": "professional",
    "status": "active",
    "billing_period": "monthly",
    "next_billing_date": "2026-07-15",
    "amount": 299.00
  },
  "users": [
    {
      "id": "user-uuid-1",
      "email": "owner@one8.com",
      "full_name": "Executive Owner",
      "platform_role": "executive_owner",
      "status": "active",
      "last_login": "2026-06-20T09:15:00Z",
      "created_at": "2026-01-15T10:35:00Z"
    },
    {
      "id": "user-uuid-2",
      "email": "admin@one8.com",
      "full_name": "Brand Admin",
      "platform_role": "brand_admin",
      "status": "active",
      "last_login": "2026-06-19T16:42:00Z",
      "created_at": "2026-01-16T11:20:00Z"
    }
  ],
  "integrations": [
    {
      "id": "int-uuid-1",
      "source_type": "shopify",
      "status": "connected",
      "last_synced": "2026-06-21T06:00:00Z"
    },
    {
      "id": "int-uuid-2",
      "source_type": "meta",
      "status": "connected",
      "last_synced": "2026-06-21T06:00:00Z"
    },
    {
      "id": "int-uuid-3",
      "source_type": "google",
      "status": "error",
      "last_synced": "2026-06-20T06:00:00Z"
    }
  ]
}
```

---

### Endpoint 3: Create Tenant + Executive Owner

**Request:**
```http
POST /admin/tenants
Authorization: Bearer <token>
Content-Type: application/json

{
  "tenant_name": "Acme D2C",
  "domain": "acme",
  "executive_owner_email": "ceo@acme.com",
  "executive_owner_full_name": "Jane Smith"
}
```

**Request Body Fields:**
- `tenant_name` (string, required): Display name (e.g., "Acme D2C")
- `domain` (string, required): URL-safe subdomain (e.g., "acme")
- `executive_owner_email` (string, required): Email for Executive Owner
- `executive_owner_full_name` (string, required): Full name of Executive Owner

**Response:** (201 Created)
```json
{
  "tenant": {
    "id": "new-tenant-uuid",
    "name": "Acme D2C",
    "domain": "acme",
    "status": "active",
    "created_at": "2026-06-21T10:00:00Z"
  },
  "executive_owner": {
    "id": "new-user-uuid",
    "email": "ceo@acme.com",
    "full_name": "Jane Smith",
    "platform_role": "executive_owner",
    "status": "invited",
    "invitation_sent": true
  },
  "subscription": {
    "id": "new-sub-uuid",
    "plan": "starter",
    "status": "trial",
    "trial_end_date": "2026-07-21"
  }
}
```

**Validation Errors:** (400 Bad Request)
```json
{
  "detail": [
    {
      "loc": ["body", "domain"],
      "msg": "Domain already exists",
      "type": "value_error"
    }
  ]
}
```

**What Happens After Creation:**
1. Tenant record created
2. Default "Starter" subscription created (14-day trial)
3. Executive Owner user created with status "invited"
4. Invitation email sent to `executive_owner_email`
5. Executive Owner must click link in email to set password

---

### Endpoint 4: Update Tenant

**Request:**
```http
PATCH /admin/tenants/{tenant_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Updated Tenant Name"
}
```

**Request Body Fields (all optional):**
- `name` (string): Update tenant display name

**Response:** (200 OK)
```json
{
  "id": "tenant-uuid",
  "name": "Updated Tenant Name",
  "domain": "acme",
  "status": "active",
  "updated_at": "2026-06-21T10:30:00Z"
}
```

---

### Endpoint 5: Change Tenant Status

**Request:**
```http
PATCH /admin/tenants/{tenant_id}/status
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "suspended",
  "reason": "Non-payment"
}
```

**Request Body:**
- `status` (enum, required): `"active"` or `"suspended"`
- `reason` (string, optional): Reason for status change

**Response:** (200 OK)
```json
{
  "id": "tenant-uuid",
  "name": "One8 Apparel",
  "status": "suspended",
  "status_changed_at": "2026-06-21T10:45:00Z",
  "status_reason": "Non-payment"
}
```

**What Happens When Suspended:**
- All tenant users are immediately logged out
- Login attempts return 403 Forbidden
- Data is preserved (read-only mode for Super Admin)
- Can be reactivated by setting `status: "active"`

---

### Endpoint 6: Delete Tenant (⚠️ DESTRUCTIVE)

**Request:**
```http
DELETE /admin/tenants/{tenant_id}
Authorization: Bearer <token>
```

**Response:** (200 OK)
```json
{
  "message": "Tenant deleted successfully",
  "tenant_id": "tenant-uuid",
  "deleted_at": "2026-06-21T11:00:00Z"
}
```

**⚠️ WARNING: This action:**
- Soft-deletes tenant (sets `deleted_at` timestamp)
- All tenant users are deleted
- All tenant data is marked as deleted (integrations, recommendations, KPIs, etc.)
- Data is NOT immediately purged (retention policy applies)
- **CANNOT BE UNDONE** via API (requires database recovery)

**Confirmation Required:**
Super Admin UI must show confirmation dialog:
```
⚠️ Delete Tenant: One8 Apparel?

This will permanently delete:
- 5 users
- 3 integrations
- All historical data
- All recommendations and simulations

Type "DELETE" to confirm:
[________]

[Cancel]  [Delete Tenant]
```

---

### Endpoint 7: Platform Health Check

**Request:**
```http
GET /api/health
```

**No authentication required**

**Response:** (200 OK)
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-06-21T12:00:00Z"
}
```

**Status Values:**
- `"healthy"` - All systems operational
- `"degraded"` - Some systems experiencing issues
- `"unhealthy"` - Critical systems down

---

### Endpoint 8: Detailed Platform Metrics (Future)

**Note:** This endpoint is NOT yet implemented in backend. Placeholder for future.

**Planned Request:**
```http
GET /admin/platform/metrics
Authorization: Bearer <token>
```

**Planned Response:**
```json
{
  "total_tenants": 15,
  "active_tenants": 12,
  "suspended_tenants": 2,
  "deleted_tenants": 1,
  "total_users": 78,
  "active_sessions": 23,
  "total_integrations": 42,
  "failed_integrations": 3,
  "recommendations_generated_today": 156,
  "api_requests_today": 8432,
  "error_rate": 0.02
}
```

**For MVP:** Super Admin can derive these metrics from tenant list.

---

## Data Models

### Tenant Model

```typescript
interface Tenant {
  id: string;                      // UUID
  name: string;                    // Display name (e.g., "One8 Apparel")
  domain: string;                  // URL-safe subdomain (e.g., "one8")
  status: 'active' | 'suspended' | 'deleted';
  subscription_plan?: string;      // e.g., "starter", "professional", "enterprise"
  seat_limit?: number;             // Maximum users allowed
  seats_used?: number;             // Current user count
  total_users?: number;            // Total users (for list view)
  total_integrations?: number;     // Total integrations (for detail view)
  created_at: string;              // ISO 8601 timestamp
  updated_at?: string;             // ISO 8601 timestamp
  deleted_at?: string | null;      // ISO 8601 timestamp if deleted
  executive_owner_email?: string;  // Primary contact email
}
```

### User Model (Simplified for Super Admin)

```typescript
interface TenantUser {
  id: string;                      // UUID
  email: string;
  full_name: string;
  platform_role: 'executive_owner' | 'brand_admin' | 'growth_manager' | 
                 'retention_manager' | 'finance_controller' | 'operations_manager';
  status: 'invited' | 'active' | 'suspended';
  last_login?: string | null;      // ISO 8601 timestamp
  created_at: string;              // ISO 8601 timestamp
}
```

### Subscription Model (Read-Only for Super Admin)

```typescript
interface Subscription {
  id: string;                      // UUID
  plan: 'starter' | 'professional' | 'enterprise';
  status: 'trial' | 'active' | 'past_due' | 'canceled';
  billing_period: 'monthly' | 'annual';
  next_billing_date?: string;      // ISO 8601 date (YYYY-MM-DD)
  trial_end_date?: string | null;  // ISO 8601 date
  amount?: number;                 // Monthly/annual price in USD
}
```

### Integration Model (Read-Only for Super Admin)

```typescript
interface Integration {
  id: string;                      // UUID
  source_type: 'shopify' | 'meta' | 'google' | 'klaviyo' | 'recharge' | 'custom';
  status: 'connected' | 'error' | 'disconnected';
  last_synced?: string | null;     // ISO 8601 timestamp
  error_message?: string | null;   // If status is 'error'
}
```

---

## Component Specifications

### Component 1: TenantTable

**Purpose:** Display list of all tenants with search, filter, and actions.

**Location:** `src/components/platform/TenantTable.tsx`

**Props:**
```typescript
interface TenantTableProps {
  tenants: Tenant[];
  loading: boolean;
  onViewDetails: (tenantId: string) => void;
  onSuspend: (tenantId: string) => void;
  onActivate: (tenantId: string) => void;
  onDelete: (tenantId: string) => void;
}
```

**Visual Specification:**

```tsx
const TenantTable: React.FC<TenantTableProps> = ({
  tenants,
  loading,
  onViewDetails,
  onSuspend,
  onActivate,
  onDelete
}) => {
  if (loading) {
    return <TenantTableSkeleton />;
  }

  return (
    <div className="bg-white shadow-sm rounded-lg border border-neutral-200 overflow-hidden">
      <table className="min-w-full divide-y divide-neutral-200">
        <thead className="bg-neutral-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
              Tenant
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
              Domain
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
              Plan
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
              Users
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">
              Created
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-neutral-200">
          {tenants.map((tenant) => (
            <tr key={tenant.id} className="hover:bg-neutral-50 transition-colors">
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  <div>
                    <div className="text-sm font-medium text-neutral-900">
                      {tenant.name}
                    </div>
                    <div className="text-sm text-neutral-500">
                      {tenant.executive_owner_email}
                    </div>
                  </div>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-700">
                {tenant.domain}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <TenantStatusBadge status={tenant.status} />
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-700 capitalize">
                {tenant.subscription_plan || 'N/A'}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-700">
                {tenant.total_users || 0}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-neutral-500">
                {formatDate(tenant.created_at)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button
                  onClick={() => onViewDetails(tenant.id)}
                  className="text-primary-600 hover:text-primary-900 mr-4"
                >
                  View
                </button>
                {tenant.status === 'active' && (
                  <button
                    onClick={() => onSuspend(tenant.id)}
                    className="text-warning-600 hover:text-warning-900 mr-4"
                  >
                    Suspend
                  </button>
                )}
                {tenant.status === 'suspended' && (
                  <button
                    onClick={() => onActivate(tenant.id)}
                    className="text-success-600 hover:text-success-900 mr-4"
                  >
                    Activate
                  </button>
                )}
                <button
                  onClick={() => onDelete(tenant.id)}
                  className="text-danger-600 hover:text-danger-900"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

**Helper Functions:**
```typescript
// src/utils/formatters.ts
export function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric' 
  });
}
```

---

### Component 2: TenantStatusBadge

**Purpose:** Visual indicator for tenant status.

**Location:** `src/components/platform/TenantStatusBadge.tsx`

**Props:**
```typescript
interface TenantStatusBadgeProps {
  status: 'active' | 'suspended' | 'deleted';
}
```

**Implementation:**
```tsx
const TenantStatusBadge: React.FC<TenantStatusBadgeProps> = ({ status }) => {
  const badgeClasses = {
    active: 'bg-success-100 text-success-800',
    suspended: 'bg-warning-100 text-warning-800',
    deleted: 'bg-neutral-100 text-neutral-800',
  };

  const labels = {
    active: 'Active',
    suspended: 'Suspended',
    deleted: 'Deleted',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badgeClasses[status]}`}>
      {labels[status]}
    </span>
  );
};
```

---

### Component 3: CreateTenantModal

**Purpose:** Modal form for creating new tenant + Executive Owner.

**Location:** `src/components/platform/CreateTenantModal.tsx`

**Props:**
```typescript
interface CreateTenantModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;  // Refresh tenant list after creation
}
```

**Implementation:**
```tsx
import { useForm } from 'react-hook-form';
import { useState } from 'react';
import apiClient from '../../api/client';

interface CreateTenantFormData {
  tenant_name: string;
  domain: string;
  executive_owner_email: string;
  executive_owner_full_name: string;
}

const CreateTenantModal: React.FC<CreateTenantModalProps> = ({
  isOpen,
  onClose,
  onSuccess
}) => {
  const { register, handleSubmit, formState: { errors }, reset } = useForm<CreateTenantFormData>();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const onSubmit = async (data: CreateTenantFormData) => {
    setIsSubmitting(true);
    setApiError(null);

    try {
      await apiClient.post('/admin/tenants', data);
      reset();
      onSuccess();
      onClose();
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail?.[0]?.msg || 
                       error.response?.data?.message || 
                       'Failed to create tenant';
      setApiError(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        {/* Backdrop */}
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6 z-10">
          <h2 className="text-xl font-semibold text-neutral-900 mb-4">
            Create New Tenant
          </h2>

          {apiError && (
            <div className="bg-danger-50 border border-danger-200 rounded-md p-3 mb-4">
              <p className="text-sm text-danger-800">{apiError}</p>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Tenant Name */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Tenant Name
              </label>
              <input
                type="text"
                {...register('tenant_name', { required: 'Tenant name is required' })}
                placeholder="e.g., Acme D2C"
                className="w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              {errors.tenant_name && (
                <p className="text-sm text-danger-600 mt-1">{errors.tenant_name.message}</p>
              )}
            </div>

            {/* Domain */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Domain (URL-safe)
              </label>
              <input
                type="text"
                {...register('domain', { 
                  required: 'Domain is required',
                  pattern: {
                    value: /^[a-z0-9-]+$/,
                    message: 'Domain must be lowercase letters, numbers, and hyphens only'
                  }
                })}
                placeholder="e.g., acme"
                className="w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              {errors.domain && (
                <p className="text-sm text-danger-600 mt-1">{errors.domain.message}</p>
              )}
            </div>

            {/* Executive Owner Email */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Executive Owner Email
              </label>
              <input
                type="email"
                {...register('executive_owner_email', { 
                  required: 'Email is required',
                  pattern: {
                    value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                    message: 'Invalid email format'
                  }
                })}
                placeholder="ceo@acme.com"
                className="w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              {errors.executive_owner_email && (
                <p className="text-sm text-danger-600 mt-1">{errors.executive_owner_email.message}</p>
              )}
            </div>

            {/* Executive Owner Full Name */}
            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                Executive Owner Full Name
              </label>
              <input
                type="text"
                {...register('executive_owner_full_name', { required: 'Full name is required' })}
                placeholder="Jane Smith"
                className="w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              {errors.executive_owner_full_name && (
                <p className="text-sm text-danger-600 mt-1">{errors.executive_owner_full_name.message}</p>
              )}
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 mt-6">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-neutral-700 bg-white border border-neutral-300 rounded-md hover:bg-neutral-50"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Creating...' : 'Create Tenant'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default CreateTenantModal;
```

---

### Component 4: DeleteTenantConfirmation

**Purpose:** Confirmation dialog for tenant deletion.

**Location:** `src/components/platform/DeleteTenantConfirmation.tsx`

**Props:**
```typescript
interface DeleteTenantConfirmationProps {
  tenant: Tenant;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
}
```

**Implementation:**
```tsx
import { useState } from 'react';

const DeleteTenantConfirmation: React.FC<DeleteTenantConfirmationProps> = ({
  tenant,
  isOpen,
  onClose,
  onConfirm
}) => {
  const [confirmText, setConfirmText] = useState('');
  const isConfirmed = confirmText === 'DELETE';

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="fixed inset-0 bg-black bg-opacity-50" onClick={onClose} />

        <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full p-6 z-10">
          <div className="flex items-center mb-4">
            <div className="flex-shrink-0 w-12 h-12 bg-danger-100 rounded-full flex items-center justify-center">
              <svg className="w-6 h-6 text-danger-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="ml-4 text-lg font-medium text-neutral-900">
              Delete Tenant: {tenant.name}?
            </h3>
          </div>

          <div className="mb-4 text-sm text-neutral-600">
            <p className="mb-2">This will permanently delete:</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>{tenant.total_users || 0} users</li>
              <li>{tenant.total_integrations || 0} integrations</li>
              <li>All historical data</li>
              <li>All recommendations and simulations</li>
            </ul>
          </div>

          <div className="bg-danger-50 border border-danger-200 rounded-md p-3 mb-4">
            <p className="text-sm text-danger-800 font-medium">
              ⚠️ This action cannot be undone
            </p>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              Type <span className="font-mono bg-neutral-100 px-1">DELETE</span> to confirm:
            </label>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              className="w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-danger-500"
              placeholder="DELETE"
            />
          </div>

          <div className="flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-neutral-700 bg-white border border-neutral-300 rounded-md hover:bg-neutral-50"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={!isConfirmed}
              className="px-4 py-2 text-sm font-medium text-white bg-danger-600 rounded-md hover:bg-danger-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Delete Tenant
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DeleteTenantConfirmation;
```

---

## Page Implementations

### Page 1: Tenant Management

**File:** `src/pages/platform/Tenants.tsx`

**Purpose:** List all tenants, create new tenants, manage tenant lifecycle.

**Full Implementation:**

```tsx
import React, { useState, useEffect } from 'react';
import apiClient from '../../api/client';
import TenantTable from '../../components/platform/TenantTable';
import CreateTenantModal from '../../components/platform/CreateTenantModal';
import DeleteTenantConfirmation from '../../components/platform/DeleteTenantConfirmation';
import { Tenant } from '../../api/types';
import { useNavigate } from 'react-router-dom';

const TenantsPage: React.FC = () => {
  const navigate = useNavigate();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [tenantToDelete, setTenantToDelete] = useState<Tenant | null>(null);

  // Fetch tenants on mount
  useEffect(() => {
    fetchTenants();
  }, []);

  const fetchTenants = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get('/admin/tenants?skip=0&limit=100');
      setTenants(response.data.tenants || []);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load tenants');
    } finally {
      setLoading(false);
    }
  };

  const handleSuspend = async (tenantId: string) => {
    if (!confirm('Suspend this tenant? Users will be immediately logged out.')) return;

    try {
      await apiClient.patch(`/admin/tenants/${tenantId}/status`, {
        status: 'suspended',
        reason: 'Admin action'
      });
      fetchTenants(); // Refresh list
    } catch (err: any) {
      alert(err.response?.data?.message || 'Failed to suspend tenant');
    }
  };

  const handleActivate = async (tenantId: string) => {
    try {
      await apiClient.patch(`/admin/tenants/${tenantId}/status`, {
        status: 'active'
      });
      fetchTenants(); // Refresh list
    } catch (err: any) {
      alert(err.response?.data?.message || 'Failed to activate tenant');
    }
  };

  const handleDeleteConfirm = async () => {
    if (!tenantToDelete) return;

    try {
      await apiClient.delete(`/admin/tenants/${tenantToDelete.id}`);
      setTenantToDelete(null);
      fetchTenants(); // Refresh list
    } catch (err: any) {
      alert(err.response?.data?.message || 'Failed to delete tenant');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Page Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900">Tenant Management</h1>
          <p className="text-sm text-neutral-600 mt-1">
            Manage all customer tenants on the AlpMark platform
          </p>
        </div>
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="inline-flex items-center px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Create Tenant
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-danger-50 border border-danger-200 rounded-md p-4 mb-6">
          <p className="text-sm text-danger-800">{error}</p>
        </div>
      )}

      {/* Tenant Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-neutral-200">
          <p className="text-sm text-neutral-600">Total Tenants</p>
          <p className="text-3xl font-semibold text-neutral-900 mt-2">
            {tenants.length}
          </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-neutral-200">
          <p className="text-sm text-neutral-600">Active Tenants</p>
          <p className="text-3xl font-semibold text-success-600 mt-2">
            {tenants.filter(t => t.status === 'active').length}
          </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-neutral-200">
          <p className="text-sm text-neutral-600">Suspended Tenants</p>
          <p className="text-3xl font-semibold text-warning-600 mt-2">
            {tenants.filter(t => t.status === 'suspended').length}
          </p>
        </div>
      </div>

      {/* Tenant Table */}
      <TenantTable
        tenants={tenants}
        loading={loading}
        onViewDetails={(id) => navigate(`/platform/tenants/${id}`)}
        onSuspend={handleSuspend}
        onActivate={handleActivate}
        onDelete={(id) => {
          const tenant = tenants.find(t => t.id === id);
          if (tenant) setTenantToDelete(tenant);
        }}
      />

      {/* Create Tenant Modal */}
      <CreateTenantModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={fetchTenants}
      />

      {/* Delete Confirmation Modal */}
      {tenantToDelete && (
        <DeleteTenantConfirmation
          tenant={tenantToDelete}
          isOpen={true}
          onClose={() => setTenantToDelete(null)}
          onConfirm={handleDeleteConfirm}
        />
      )}
    </div>
  );
};

export default TenantsPage;
```

---

### Page 2: Tenant Details

**File:** `src/pages/platform/TenantDetails.tsx`

**Purpose:** View detailed information about a single tenant.

**Full Implementation:**

```tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../../api/client';
import TenantStatusBadge from '../../components/platform/TenantStatusBadge';

interface TenantDetails {
  id: string;
  name: string;
  domain: string;
  status: 'active' | 'suspended' | 'deleted';
  subscription_plan?: string;
  seat_limit?: number;
  seats_used?: number;
  total_users: number;
  total_integrations: number;
  created_at: string;
  updated_at?: string;
  executive_owner_email?: string;
  subscription?: any;
  users?: any[];
  integrations?: any[];
}

const TenantDetailsPage: React.FC = () => {
  const { tenant_id } = useParams<{ tenant_id: string }>();
  const navigate = useNavigate();
  const [tenant, setTenant] = useState<TenantDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTenantDetails();
  }, [tenant_id]);

  const fetchTenantDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.get(`/admin/tenants/${tenant_id}`);
      setTenant(response.data);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load tenant details');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <p className="text-neutral-600">Loading tenant details...</p>
      </div>
    );
  }

  if (error || !tenant) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-danger-50 border border-danger-200 rounded-md p-4">
          <p className="text-sm text-danger-800">{error || 'Tenant not found'}</p>
        </div>
        <button
          onClick={() => navigate('/platform/tenants')}
          className="mt-4 text-primary-600 hover:text-primary-800"
        >
          ← Back to Tenants
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Back Button */}
      <button
        onClick={() => navigate('/platform/tenants')}
        className="mb-6 text-primary-600 hover:text-primary-800 flex items-center"
      >
        <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to Tenants
      </button>

      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900">{tenant.name}</h1>
          <p className="text-sm text-neutral-600 mt-1">{tenant.domain}</p>
        </div>
        <TenantStatusBadge status={tenant.status} />
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border border-neutral-200">
          <p className="text-sm text-neutral-600">Total Users</p>
          <p className="text-3xl font-semibold text-neutral-900 mt-2">
            {tenant.total_users}
          </p>
          <p className="text-xs text-neutral-500 mt-1">
            {tenant.seats_used || 0} / {tenant.seat_limit || 'Unlimited'} seats
          </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-neutral-200">
          <p className="text-sm text-neutral-600">Integrations</p>
          <p className="text-3xl font-semibold text-neutral-900 mt-2">
            {tenant.total_integrations}
          </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-neutral-200">
          <p className="text-sm text-neutral-600">Plan</p>
          <p className="text-xl font-semibold text-neutral-900 mt-2 capitalize">
            {tenant.subscription_plan || 'N/A'}
          </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-sm border border-neutral-200">
          <p className="text-sm text-neutral-600">Created</p>
          <p className="text-sm font-medium text-neutral-900 mt-2">
            {new Date(tenant.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>

      {/* Subscription Details */}
      {tenant.subscription && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-neutral-200 mb-6">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Subscription</h2>
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm text-neutral-600">Plan</dt>
              <dd className="text-sm font-medium text-neutral-900 capitalize">
                {tenant.subscription.plan}
              </dd>
            </div>
            <div>
              <dt className="text-sm text-neutral-600">Status</dt>
              <dd className="text-sm font-medium text-neutral-900 capitalize">
                {tenant.subscription.status}
              </dd>
            </div>
            <div>
              <dt className="text-sm text-neutral-600">Billing Period</dt>
              <dd className="text-sm font-medium text-neutral-900 capitalize">
                {tenant.subscription.billing_period}
              </dd>
            </div>
            <div>
              <dt className="text-sm text-neutral-600">Next Billing Date</dt>
              <dd className="text-sm font-medium text-neutral-900">
                {tenant.subscription.next_billing_date || 'N/A'}
              </dd>
            </div>
          </dl>
        </div>
      )}

      {/* Users Table */}
      {tenant.users && tenant.users.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-neutral-200 mb-6">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Users</h2>
          <table className="min-w-full divide-y divide-neutral-200">
            <thead>
              <tr>
                <th className="text-left text-xs font-medium text-neutral-500 uppercase pb-3">Email</th>
                <th className="text-left text-xs font-medium text-neutral-500 uppercase pb-3">Name</th>
                <th className="text-left text-xs font-medium text-neutral-500 uppercase pb-3">Role</th>
                <th className="text-left text-xs font-medium text-neutral-500 uppercase pb-3">Status</th>
                <th className="text-left text-xs font-medium text-neutral-500 uppercase pb-3">Last Login</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200">
              {tenant.users.map((user) => (
                <tr key={user.id}>
                  <td className="py-3 text-sm text-neutral-900">{user.email}</td>
                  <td className="py-3 text-sm text-neutral-700">{user.full_name}</td>
                  <td className="py-3 text-sm text-neutral-700 capitalize">
                    {user.platform_role.replace('_', ' ')}
                  </td>
                  <td className="py-3 text-sm capitalize">{user.status}</td>
                  <td className="py-3 text-sm text-neutral-600">
                    {user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Integrations Table */}
      {tenant.integrations && tenant.integrations.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-neutral-200">
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Integrations</h2>
          <table className="min-w-full divide-y divide-neutral-200">
            <thead>
              <tr>
                <th className="text-left text-xs font-medium text-neutral-500 uppercase pb-3">Source</th>
                <th className="text-left text-xs font-medium text-neutral-500 uppercase pb-3">Status</th>
                <th className="text-left text-xs font-medium text-neutral-500 uppercase pb-3">Last Synced</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200">
              {tenant.integrations.map((integration) => (
                <tr key={integration.id}>
                  <td className="py-3 text-sm text-neutral-900 capitalize">{integration.source_type}</td>
                  <td className="py-3">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                      integration.status === 'connected' 
                        ? 'bg-success-100 text-success-800'
                        : 'bg-danger-100 text-danger-800'
                    }`}>
                      {integration.status}
                    </span>
                  </td>
                  <td className="py-3 text-sm text-neutral-600">
                    {integration.last_synced 
                      ? new Date(integration.last_synced).toLocaleString() 
                      : 'Never'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default TenantDetailsPage;
```

---

### Page 3: System Health (Placeholder)

**File:** `src/pages/platform/SystemHealth.tsx`

**Note:** Backend endpoint not yet implemented. This is a placeholder.

```tsx
import React from 'react';

const SystemHealthPage: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-semibold text-neutral-900 mb-6">System Health</h1>
      
      <div className="bg-warning-50 border border-warning-200 rounded-md p-4">
        <p className="text-sm text-warning-800">
          ⚠️ System health monitoring is not yet implemented in the backend.
        </p>
        <p className="text-sm text-warning-700 mt-2">
          Planned features: API health, database status, integration sync status, error rates.
        </p>
      </div>
    </div>
  );
};

export default SystemHealthPage;
```

---

## Navigation & Routing

### Super Admin Sidebar Navigation

**File:** `src/components/layout/SuperAdminSidebar.tsx`

```tsx
import React from 'react';
import { NavLink } from 'react-router-dom';

const SuperAdminSidebar: React.FC = () => {
  const navItems = [
    {
      name: 'Tenants',
      path: '/platform/tenants',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
        </svg>
      ),
    },
    {
      name: 'System Health',
      path: '/platform/health',
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
    },
  ];

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-white border-r border-neutral-200">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-neutral-200">
        <span className="text-xl font-semibold text-primary-600">AlpMark</span>
        <span className="ml-2 text-xs bg-neutral-100 px-2 py-0.5 rounded text-neutral-700">
          Admin
        </span>
      </div>

      {/* Navigation */}
      <nav className="mt-6 px-3">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center px-3 py-2 mb-1 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary-50 text-primary-700 border-l-4 border-primary-600'
                  : 'text-neutral-700 hover:bg-neutral-100'
              }`
            }
          >
            <span className="mr-3">{item.icon}</span>
            {item.name}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
};

export default SuperAdminSidebar;
```

### React Router Setup

**File:** `src/App.tsx`

```tsx
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/auth/ProtectedRoute';

// Pages
import LoginPage from './pages/Login';
import TenantsPage from './pages/platform/Tenants';
import TenantDetailsPage from './pages/platform/TenantDetails';
import SystemHealthPage from './pages/platform/SystemHealth';

// Layout
import SuperAdminLayout from './components/layout/SuperAdminLayout';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<LoginPage />} />

          {/* Super Admin Routes */}
          <Route
            path="/platform/*"
            element={
              <ProtectedRoute allowedRoles={['super_admin']}>
                <SuperAdminLayout>
                  <Routes>
                    <Route path="tenants" element={<TenantsPage />} />
                    <Route path="tenants/:tenant_id" element={<TenantDetailsPage />} />
                    <Route path="health" element={<SystemHealthPage />} />
                    <Route path="*" element={<Navigate to="/platform/tenants" replace />} />
                  </Routes>
                </SuperAdminLayout>
              </ProtectedRoute>
            }
          />

          {/* Default Redirect */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
```

---

## Step-by-Step Build Instructions

### Step 1: Project Setup

```bash
# Create Vite React + TypeScript project
npm create vite@latest alpmark-frontend -- --template react-ts
cd alpmark-frontend

# Install dependencies
npm install react-router-dom axios react-hook-form date-fns

# Install Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Install Heroicons
npm install @heroicons/react
```

### Step 2: Configure Tailwind

**File:** `tailwind.config.js`

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        success: {
          50: '#f0fdf4',
          100: '#dcfce7',
          200: '#bbf7d0',
          600: '#16a34a',
          800: '#166534',
        },
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          600: '#d97706',
          800: '#92400e',
        },
        danger: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          600: '#dc2626',
          800: '#991b1b',
        },
        neutral: {
          50: '#fafafa',
          100: '#f5f5f5',
          200: '#e5e5e5',
          300: '#d4d4d4',
          500: '#737373',
          600: '#525252',
          700: '#404040',
          800: '#262626',
          900: '#171717',
        },
      },
    },
  },
  plugins: [],
}
```

**File:** `src/index.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### Step 3: Create API Client

**File:** `src/api/client.ts`

```typescript
import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://alpmark-production.up.railway.app';

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('alpmark_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('alpmark_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

### Step 4: Create TypeScript Types

**File:** `src/api/types.ts`

```typescript
export interface Tenant {
  id: string;
  name: string;
  domain: string;
  status: 'active' | 'suspended' | 'deleted';
  subscription_plan?: string;
  seat_limit?: number;
  seats_used?: number;
  total_users?: number;
  total_integrations?: number;
  created_at: string;
  updated_at?: string;
  executive_owner_email?: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  platform_role: string;
  status: string;
  last_login?: string | null;
  created_at: string;
}
```

### Step 5: Create Auth Context

**File:** `src/contexts/AuthContext.tsx`

```typescript
import React, { createContext, useContext, useState, useEffect } from 'react';
import apiClient from '../api/client';

interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  platform_role: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    // Check if token exists on mount
    const token = localStorage.getItem('alpmark_token');
    if (token) {
      fetchCurrentUser();
    }
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const response = await apiClient.get('/api/auth/me');
      setUser(response.data);
    } catch {
      localStorage.removeItem('alpmark_token');
    }
  };

  const login = async (email: string, password: string) => {
    const response = await apiClient.post('/api/auth/login', { email, password });
    localStorage.setItem('alpmark_token', response.data.access_token);
    setUser(response.data.user);
  };

  const logout = () => {
    localStorage.removeItem('alpmark_token');
    setUser(null);
    window.location.href = '/login';
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
```

### Step 6: Create Protected Route

**File:** `src/components/auth/ProtectedRoute.tsx`

```typescript
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles: string[];
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!allowedRoles.includes(user!.platform_role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
```

### Step 7: Build Components (in order)

1. `TenantStatusBadge.tsx` (simplest)
2. `TenantTable.tsx`
3. `CreateTenantModal.tsx`
4. `DeleteTenantConfirmation.tsx`
5. `SuperAdminSidebar.tsx`
6. `SuperAdminLayout.tsx`

### Step 8: Build Pages (in order)

1. `LoginPage.tsx`
2. `TenantsPage.tsx`
3. `TenantDetailsPage.tsx`
4. `SystemHealthPage.tsx` (placeholder)

### Step 9: Environment Variables

**File:** `.env`

```
VITE_API_URL=https://alpmark-production.up.railway.app
```

### Step 10: Test with Real Data

**Login as Super Admin:**
- Email: `admin@alpmark.com` (or create one via backend)
- Password: Your password

**Test Flow:**
1. Login → should redirect to `/platform/tenants`
2. Click "Create Tenant" → fill form → submit
3. Verify tenant appears in list
4. Click "View" → verify details page loads
5. Test suspend/activate/delete actions

---

## Summary

This guide provides **everything** needed to build the Super Admin frontend:

✅ **3 pages** with full implementations  
✅ **8 API endpoints** with exact request/response formats  
✅ **4 core components** with complete code  
✅ **TypeScript types** for all data models  
✅ **Authentication** with JWT token management  
✅ **Routing** with React Router  
✅ **Step-by-step build instructions**  

**Total Implementation Time:** ~4-6 hours for experienced React developer

**Next Persona:** Executive Owner (customer dashboard with KPIs, alerts, recommendations)

---

**End of Super Admin Guide**

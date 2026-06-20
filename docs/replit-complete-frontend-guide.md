# AlpMark Intelligence Platform - Complete Frontend Implementation Guide for Replit

**Version 1.0**  
**Created: 2026-06-20**

---

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Frontend Philosophy](#frontend-philosophy)
4. [Frontend Architecture & Design System](#frontend-architecture--design-system)
5. [Backend API Reference](#backend-api-reference)
6. [Authentication & Identity](#authentication--identity)
7. [Persona Dashboard Specifications](#persona-dashboard-specifications)
8. [Supporting Systems](#supporting-systems)
9. [Data Models & Relationships](#data-models--relationships)
10. [Feature Flags & Subscription Plans](#feature-flags--subscription-plans)
11. [Step-by-Step Build Instructions](#step-by-step-build-instructions)

---

## Introduction

AlpMark is a multi-tenant Business Intelligence and Decision Support Platform designed for D2C e-commerce brands. This document provides complete instructions for building the frontend application that connects to the existing backend (178 operational endpoints, 880 tests passing).

### What AlpMark Is

- **Intelligence platform**, not a dashboard
- Answers: "What? Why? Opportunities? Risks? What if?"
- Not just: "What happened?"

### Current Backend Status

- **Endpoints**: 178 operational across 14 domains
- **Tests**: 880/881 passing
- **Quality**: ruff clean (0 errors), mypy clean (0 errors)
- **Database**: PostgreSQL on Railway (production)
- **Authentication**: JWT with HS256, invitation-only system
- **Demo Data**: seed_one8.py generates 90-day historical data for "one8" tenant

### Three Distinct Products

AlpMark is NOT one frontend - it's three:

1. **Business Intelligence Product** (5 personas: Executive Owner, Growth Manager, Retention Manager, Finance Controller, Operations Manager)
2. **Tenant Administration Product** (Brand Admin)
3. **Platform Operations Product** (Super Admin, Support Operator)

Each product has distinct navigation, pages, and purpose.

---

## Architecture Overview

### Tenant Isolation

**Core Principle**: Every tenant is completely isolated.

- Each tenant has own: users, integrations, data, recommendations, simulations, billing
- NO cross-tenant data access under any circumstances
- Users belong to ONE tenant only

### Invitation-Only System

**NO public registration** - every user is invited.

**Flow**:
```
Super Admin creates Tenant + Executive Owner
  ↓
Executive Owner invited via email
  ↓
Executive Owner creates password → logs in
  ↓
Executive Owner invites Brand Admin
  ↓
Brand Admin configures workspace (integrations, users)
  ↓
Brand Admin invites department users
  ↓
Team uses business intelligence
```

### User Hierarchy

1. **Super Admin** (AlpMark employee)
   - Creates tenants
   - Manages subscription plans
   - Configures feature availability
   - Cannot: access customer business data

2. **Executive Owner** (Customer - highest authority)
   - Views all business dashboards
   - Views recommendations & simulations
   - Can invite Brand Admin
   - Cannot: configure workspace

3. **Brand Admin** (Customer - workspace manager)
   - Manages users, roles, billing, integrations
   - Does NOT see business intelligence
   - Does NOT see recommendations/simulations

4. **Department Users** (Growth Manager, Retention Manager, Finance Controller, Operations Manager)
   - View dashboards relevant to their department only
   - Cannot: manage users, billing, integrations

5. **Support Operator** (AlpMark employee)
   - Read-only access for troubleshooting
   - Cannot: modify customer data

### Authentication

**Technology**: JWT with HS256 algorithm

**Key Details**:
- Secret: `AUTH_JWT_SECRET="alpmark-dev-secret-alpmark-dev-secret-2026"`
- Token subject: **email** (NOT UUID)
- Token claims: `{sub: email, email: email, platform_role: role}`
- Sessions: persistent, can manage active sessions
- Password reset: email-based token flow

**Important**: `jwt.subject` contains the user's email, NOT their UUID. Endpoints resolve user via:
```python
user = db.scalar(select(User).where(User.email == auth.email))
```

### Multi-Tenant Data Model

**Core Entities**:
- `Tenant`: Top-level isolation boundary
- `User`: Belongs to one tenant, has one platform_role
- `Subscription`: Defines plan, seat limit, feature availability
- `Integration`: Tenant-specific data connections
- All business data: scoped by tenant_id

---

## Frontend Philosophy

### Not a Dashboard

AlpMark is NOT:
- Power BI
- Tableau
- Excel
- Google Analytics

Those systems answer: **"What happened?"**

AlpMark answers:
- What happened?
- **Why did it happen?**
- **What patterns exist?**
- **What opportunities exist?**
- **What are the risks?**
- **What happens if assumptions change?**

### Design Inspiration

- **Bloomberg** for business intelligence
- **Linear** for clarity
- **Notion** for explainability
- **GitHub** for transparency

### Visual Distribution

Every business intelligence page should target:
- **60%** Charts
- **25%** KPI Cards
- **15%** Tables

Large empty spaces should rarely exist. Every component must earn its place.

### KPI Cards Are Interactive

Every KPI card must show:
- Current value
- Percentage change
- Trend indicator
- **Confidence score** (87%, "High")
- **Last updated timestamp**
- **Info button** → explainability modal

**Explainability Modal** shows:
- Definition (plain English)
- Formula
- Data sources (✓ Shopify, ✓ Meta, etc.)
- Last synced timestamp
- Confidence explanation

### Navigation Principles

1. **Role-specific** - only show what's relevant to current user
2. **Frequently visited pages** come first (not alphabetical)
3. **Hidden features** should not exist visually (no disabled menu items)
4. If feature is disabled: page/button/nav item should NOT appear

### Empty States

Bad: "No Data"

Good: "No recommendations are currently available. AlpMark requires sufficient historical data before generating recommendations. Connect additional data sources or wait for the next synchronization."

Always explain: Why empty? What happens next? What action is required?

### Loading States

Use **skeleton loading** for all major components:
- Charts → skeleton chart shape
- KPI cards → skeleton card
- Tables → skeleton rows
- Recommendations → skeleton recommendation

Never show: generic spinners or "Loading..."

---

## Frontend Architecture & Design System

This section provides complete technical specifications for implementing the AlpMark frontend - no guesswork required.

### Technology Stack

**Required Stack**:
```
Framework: React 18+
Language: TypeScript 5+
Build Tool: Vite
Routing: React Router v6
HTTP Client: Axios
State Management: React Context + Custom Hooks
Styling: Tailwind CSS 3+
Charts: Recharts
Forms: React Hook Form
Date Handling: date-fns
Icons: Heroicons
```

### Project Structure

```
src/
├── main.tsx                    # Entry point
├── App.tsx                     # Root component with routing
├── vite-env.d.ts              # TypeScript definitions
│
├── api/                        # API client layer
│   ├── client.ts              # Axios instance with interceptors
│   ├── auth.ts                # Authentication API calls
│   ├── executive.ts           # Executive dashboard API calls
│   ├── growth.ts              # Growth dashboard API calls
│   ├── retention.ts           # Retention dashboard API calls
│   ├── finance.ts             # Finance dashboard API calls
│   ├── operations.ts          # Operations dashboard API calls
│   ├── recommendations.ts     # Recommendations API calls
│   ├── simulations.ts         # Simulations API calls
│   ├── alerts.ts              # Alerts API calls
│   ├── admin.ts               # Admin API calls
│   └── types.ts               # API TypeScript interfaces
│
├── components/                 # Reusable components
│   ├── layout/
│   │   ├── AppShell.tsx       # Main layout with nav + header
│   │   ├── Sidebar.tsx        # Navigation sidebar
│   │   ├── Header.tsx         # Top header with user menu
│   │   └── PageContainer.tsx  # Consistent page wrapper
│   │
│   ├── cards/
│   │   ├── KPICard.tsx        # KPI display card
│   │   ├── MetricCard.tsx     # Simple metric card
│   │   └── InsightCard.tsx    # Insight/alert card
│   │
│   ├── charts/
│   │   ├── LineChart.tsx      # Time-series line chart
│   │   ├── BarChart.tsx       # Bar chart
│   │   ├── AreaChart.tsx      # Area chart
│   │   ├── ComposedChart.tsx  # Multi-series composed chart
│   │   └── ChartContainer.tsx # Chart wrapper with loading/error
│   │
│   ├── recommendations/
│   │   ├── RecommendationCard.tsx      # Single recommendation
│   │   ├── RecommendationList.tsx      # List of recommendations
│   │   └── ExplainabilityModal.tsx     # Explanation modal
│   │
│   ├── simulations/
│   │   ├── SimulationTable.tsx         # Simulation results table
│   │   ├── SimulationForm.tsx          # Run simulation form
│   │   └── ScenarioComparison.tsx      # Scenario comparison view
│   │
│   ├── alerts/
│   │   ├── AlertBanner.tsx             # Alert notification banner
│   │   └── AlertList.tsx               # List of alerts
│   │
│   ├── tables/
│   │   ├── DataTable.tsx               # Generic data table
│   │   └── SortableTable.tsx           # Sortable table component
│   │
│   └── common/
│       ├── Button.tsx                  # Button component
│       ├── Input.tsx                   # Input component
│       ├── Select.tsx                  # Select dropdown
│       ├── Modal.tsx                   # Modal dialog
│       ├── Badge.tsx                   # Badge/tag component
│       ├── Skeleton.tsx                # Skeleton loader
│       ├── EmptyState.tsx              # Empty state component
│       ├── ErrorState.tsx              # Error state component
│       └── LoadingSpinner.tsx          # Loading spinner
│
├── contexts/                   # React contexts
│   ├── AuthContext.tsx        # Authentication state
│   ├── TenantContext.tsx      # Tenant information
│   └── FeatureFlagContext.tsx # Feature flags
│
├── hooks/                      # Custom React hooks
│   ├── useAuth.ts             # Authentication hook
│   ├── useApi.ts              # API call wrapper hook
│   ├── useFeatureFlag.ts      # Feature flag check hook
│   ├── useDebounce.ts         # Debounce hook
│   └── useLocalStorage.ts     # LocalStorage hook
│
├── pages/                      # Page components
│   ├── Login.tsx              # Login page
│   ├── ForgotPassword.tsx     # Forgot password page
│   ├── ResetPassword.tsx      # Reset password page
│   │
│   ├── executive/
│   │   └── Dashboard.tsx      # Executive Owner dashboard
│   │
│   ├── growth/
│   │   └── Dashboard.tsx      # Growth Manager dashboard
│   │
│   ├── retention/
│   │   └── Dashboard.tsx      # Retention Manager dashboard
│   │
│   ├── finance/
│   │   └── Dashboard.tsx      # Finance Controller dashboard
│   │
│   ├── operations/
│   │   └── Dashboard.tsx      # Operations Manager dashboard
│   │
│   ├── admin/
│   │   ├── Dashboard.tsx      # Brand Admin dashboard
│   │   ├── Users.tsx          # User management
│   │   ├── Integrations.tsx   # Integration setup
│   │   └── Billing.tsx        # Billing management
│   │
│   └── platform/
│       ├── Tenants.tsx        # Super Admin tenant list
│       ├── Support.tsx        # Support operator dashboard
│       └── SystemHealth.tsx   # System health monitoring
│
├── utils/                      # Utility functions
│   ├── formatters.ts          # Number/date formatters
│   ├── validators.ts          # Validation functions
│   ├── calculations.ts        # Business logic calculations
│   └── constants.ts           # App constants
│
└── styles/                     # Global styles
    ├── index.css              # Global CSS + Tailwind imports
    └── tailwind.config.js     # Tailwind configuration
```

### Design Tokens

**Color Palette**:
```typescript
// colors defined in tailwind.config.js
const colors = {
  // Brand Colors
  primary: {
    50: '#f0f9ff',
    100: '#e0f2fe',
    200: '#bae6fd',
    300: '#7dd3fc',
    400: '#38bdf8',
    500: '#0ea5e9',  // Primary brand color
    600: '#0284c7',
    700: '#0369a1',
    800: '#075985',
    900: '#0c4a6e',
  },
  
  // Neutral Grays
  neutral: {
    50: '#fafafa',
    100: '#f4f4f5',
    200: '#e4e4e7',
    300: '#d4d4d8',
    400: '#a1a1aa',
    500: '#71717a',
    600: '#52525b',
    700: '#3f3f46',
    800: '#27272a',
    900: '#18181b',
  },
  
  // Semantic Colors
  success: {
    50: '#f0fdf4',
    500: '#22c55e',  // Green for positive metrics
    600: '#16a34a',
  },
  
  warning: {
    50: '#fffbeb',
    500: '#f59e0b',  // Amber for warnings
    600: '#d97706',
  },
  
  danger: {
    50: '#fef2f2',
    500: '#ef4444',  // Red for negative metrics
    600: '#dc2626',
  },
  
  info: {
    50: '#eff6ff',
    500: '#3b82f6',  // Blue for informational
    600: '#2563eb',
  },
};
```

**Typography Scale**:
```typescript
const typography = {
  // Font Families
  fontFamily: {
    sans: ['Inter', 'system-ui', 'sans-serif'],
    mono: ['JetBrains Mono', 'monospace'],
  },
  
  // Font Sizes (Tailwind classes)
  fontSize: {
    'xs': '0.75rem',      // 12px - labels, badges
    'sm': '0.875rem',     // 14px - secondary text
    'base': '1rem',       // 16px - body text
    'lg': '1.125rem',     // 18px - emphasized text
    'xl': '1.25rem',      // 20px - section headers
    '2xl': '1.5rem',      // 24px - KPI values
    '3xl': '1.875rem',    // 30px - page titles
    '4xl': '2.25rem',     // 36px - hero numbers
  },
  
  // Font Weights
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
};
```

**Spacing Scale** (Tailwind default - use consistently):
```
0: 0px
1: 0.25rem (4px)
2: 0.5rem (8px)
3: 0.75rem (12px)
4: 1rem (16px)
5: 1.25rem (20px)
6: 1.5rem (24px)
8: 2rem (32px)
10: 2.5rem (40px)
12: 3rem (48px)
16: 4rem (64px)
```

**Shadow Scale**:
```css
shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05)
shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)
shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)
shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)
shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)
```

**Border Radius**:
```
rounded-sm: 0.125rem (2px)
rounded: 0.25rem (4px)
rounded-md: 0.375rem (6px)
rounded-lg: 0.5rem (8px)
rounded-xl: 0.75rem (12px)
rounded-2xl: 1rem (16px)
```

### Component Library Specifications

#### KPICard Component

**Purpose**: Display key performance indicators with value, trend, and interaction.

**Props**:
```typescript
interface KPICardProps {
  title: string;              // KPI name (e.g., "Contribution Margin %")
  value: number | string;     // Current value
  unit?: string;              // Unit (%, $, etc.)
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: number;        // Percentage change
  comparisonPeriod?: string;  // e.g., "vs last month"
  onClick?: () => void;       // Click handler for drill-down
  loading?: boolean;
  error?: string;
}
```

**Visual Specification**:
```tsx
// Example implementation
const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  unit,
  trend,
  trendValue,
  comparisonPeriod,
  onClick,
  loading,
  error
}) => {
  if (loading) return <KPICardSkeleton />;
  if (error) return <KPICardError error={error} />;
  
  return (
    <div 
      className="bg-white p-6 rounded-lg shadow-sm border border-neutral-200 hover:shadow-md transition-shadow cursor-pointer"
      onClick={onClick}
    >
      {/* Title */}
      <h3 className="text-sm font-medium text-neutral-600 mb-2">
        {title}
      </h3>
      
      {/* Value */}
      <div className="flex items-baseline gap-2 mb-1">
        <span className="text-3xl font-bold text-neutral-900">
          {unit === '$' && '$'}
          {value}
          {unit && unit !== '$' && unit}
        </span>
      </div>
      
      {/* Trend */}
      {trend && trendValue !== undefined && (
        <div className={`flex items-center gap-1 text-sm ${
          trend === 'up' ? 'text-success-600' : 
          trend === 'down' ? 'text-danger-600' : 
          'text-neutral-500'
        }`}>
          {trend === 'up' && <ArrowUpIcon className="w-4 h-4" />}
          {trend === 'down' && <ArrowDownIcon className="w-4 h-4" />}
          <span className="font-medium">
            {trendValue > 0 && '+'}{trendValue}%
          </span>
          {comparisonPeriod && (
            <span className="text-neutral-500">{comparisonPeriod}</span>
          )}
        </div>
      )}
    </div>
  );
};
```

**Usage Rules**:
- Always show loading skeleton during data fetch
- Show error state if API call fails
- Trend color: green = good, red = bad (context-aware)
- Make clickable for drill-down (show cursor-pointer)
- Grid layout: 3-4 cards per row on desktop, 1 on mobile

#### RecommendationCard Component

**Purpose**: Display actionable recommendations with explainability.

**Props**:
```typescript
interface RecommendationCardProps {
  recommendation: {
    id: string;
    title: string;
    description: string;
    priority: 'critical' | 'high' | 'medium' | 'low';
    confidence_score: number;  // 0-100
    expected_impact_usd?: number;
    domain: string;
    status: string;
    created_at: string;
    explainability?: {
      why_now: string;
      key_factors: string[];
      risks: string[];
      expected_outcome: string;
    };
  };
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
  onViewDetails?: (id: string) => void;
}
```

**Visual Specification**:
```tsx
const RecommendationCard: React.FC<RecommendationCardProps> = ({
  recommendation,
  onApprove,
  onReject,
  onViewDetails
}) => {
  const [showExplainability, setShowExplainability] = useState(false);
  
  const priorityColors = {
    critical: 'border-danger-500 bg-danger-50',
    high: 'border-warning-500 bg-warning-50',
    medium: 'border-info-500 bg-info-50',
    low: 'border-neutral-300 bg-neutral-50',
  };
  
  return (
    <>
      <div className={`p-6 rounded-lg border-l-4 ${priorityColors[recommendation.priority]}`}>
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div>
            <h4 className="text-lg font-semibold text-neutral-900 mb-1">
              {recommendation.title}
            </h4>
            <div className="flex items-center gap-3 text-sm text-neutral-600">
              <Badge variant={recommendation.priority}>{recommendation.priority.toUpperCase()}</Badge>
              <span>Confidence: {recommendation.confidence_score}%</span>
              <span>{recommendation.domain}</span>
            </div>
          </div>
          {recommendation.expected_impact_usd && (
            <div className="text-right">
              <div className="text-sm text-neutral-600">Expected Impact</div>
              <div className="text-xl font-bold text-success-600">
                +${formatNumber(recommendation.expected_impact_usd)}
              </div>
            </div>
          )}
        </div>
        
        {/* Description */}
        <p className="text-neutral-700 mb-4">
          {recommendation.description}
        </p>
        
        {/* Actions */}
        <div className="flex items-center gap-3">
          <Button 
            variant="primary" 
            size="sm"
            onClick={() => onApprove?.(recommendation.id)}
          >
            Approve
          </Button>
          <Button 
            variant="secondary" 
            size="sm"
            onClick={() => onReject?.(recommendation.id)}
          >
            Reject
          </Button>
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => setShowExplainability(true)}
          >
            <InformationCircleIcon className="w-4 h-4 mr-1" />
            Why this recommendation?
          </Button>
        </div>
      </div>
      
      {/* Explainability Modal */}
      {showExplainability && recommendation.explainability && (
        <ExplainabilityModal
          explainability={recommendation.explainability}
          onClose={() => setShowExplainability(false)}
        />
      )}
    </>
  );
};
```

#### ChartContainer Component

**Purpose**: Wrapper for all charts with consistent loading/error/empty states.

**Props**:
```typescript
interface ChartContainerProps {
  title: string;
  subtitle?: string;
  loading?: boolean;
  error?: string;
  empty?: boolean;
  emptyMessage?: string;
  children: React.ReactNode;
  actions?: React.ReactNode;  // Filter buttons, export, etc.
}
```

**Visual Specification**:
```tsx
const ChartContainer: React.FC<ChartContainerProps> = ({
  title,
  subtitle,
  loading,
  error,
  empty,
  emptyMessage,
  children,
  actions
}) => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-neutral-200">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-neutral-900">{title}</h3>
          {subtitle && (
            <p className="text-sm text-neutral-600 mt-1">{subtitle}</p>
          )}
        </div>
        {actions && <div className="flex gap-2">{actions}</div>}
      </div>
      
      {/* Content */}
      {loading && <ChartSkeleton />}
      {error && <ErrorState message={error} />}
      {empty && <EmptyState message={emptyMessage || 'No data available'} />}
      {!loading && !error && !empty && (
        <div className="w-full h-80">
          {children}
        </div>
      )}
    </div>
  );
};
```

#### Button Component

**Purpose**: Consistent button styling across the app.

**Props**:
```typescript
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'xs' | 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
  disabled?: boolean;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  onClick?: () => void;
  children: React.ReactNode;
}
```

**Visual Specification**:
```tsx
const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  disabled = false,
  loading = false,
  leftIcon,
  rightIcon,
  onClick,
  children
}) => {
  const baseClasses = 'inline-flex items-center justify-center font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2';
  
  const variantClasses = {
    primary: 'bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500 disabled:bg-neutral-300',
    secondary: 'bg-neutral-100 text-neutral-900 hover:bg-neutral-200 focus:ring-neutral-500 disabled:bg-neutral-100',
    danger: 'bg-danger-600 text-white hover:bg-danger-700 focus:ring-danger-500 disabled:bg-neutral-300',
    ghost: 'bg-transparent text-neutral-700 hover:bg-neutral-100 focus:ring-neutral-500',
  };
  
  const sizeClasses = {
    xs: 'px-2.5 py-1.5 text-xs',
    sm: 'px-3 py-2 text-sm',
    md: 'px-4 py-2.5 text-base',
    lg: 'px-6 py-3 text-lg',
  };
  
  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${fullWidth ? 'w-full' : ''}`}
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading && <LoadingSpinner className="w-4 h-4 mr-2" />}
      {!loading && leftIcon && <span className="mr-2">{leftIcon}</span>}
      {children}
      {rightIcon && <span className="ml-2">{rightIcon}</span>}
    </button>
  );
};
```

### Layout System

#### AppShell Component

**Purpose**: Main layout wrapper with sidebar navigation and header.

**Structure**:
```tsx
const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main Content Area */}
      <div className="pl-64">  {/* Offset for fixed sidebar */}
        <Header />
        <main className="p-8">
          {children}
        </main>
      </div>
    </div>
  );
};
```

#### Sidebar Navigation

**Specification**:
- Fixed left sidebar, 256px wide (w-64)
- Background: white with shadow-lg
- Logo at top (48px height)
- Navigation items grouped by section
- Active state: primary-50 background, primary-600 text, left border accent
- Hover state: neutral-100 background
- Icons: Heroicons (24px)

**Example Implementation**:
```tsx
const Sidebar: React.FC = () => {
  const { user } = useAuth();
  const location = useLocation();
  
  // Navigation items based on user role
  const navItems = getNavItemsForRole(user.role);
  
  return (
    <div className="fixed inset-y-0 left-0 w-64 bg-white shadow-lg">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-neutral-200">
        <img src="/alpmark-logo.svg" alt="AlpMark" className="h-8" />
      </div>
      
      {/* Navigation */}
      <nav className="p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-md text-sm font-medium transition-colors ${
                isActive 
                  ? 'bg-primary-50 text-primary-600 border-l-4 border-primary-600' 
                  : 'text-neutral-700 hover:bg-neutral-100'
              }`}
            >
              <item.icon className="w-5 h-5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      
      {/* User Info at Bottom */}
      <div className="absolute bottom-0 w-full p-4 border-t border-neutral-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
            <span className="text-primary-600 font-semibold">
              {user.email[0].toUpperCase()}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-neutral-900 truncate">
              {user.email}
            </p>
            <p className="text-xs text-neutral-600 truncate">
              {user.role}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
```

#### Header Component

**Specification**:
- Sticky top header, 64px height
- Background: white with bottom border
- Left: Page title
- Right: Notification bell, user menu dropdown
- Breadcrumb navigation (optional)

#### PageContainer Component

**Purpose**: Consistent page wrapper with title and actions.

```tsx
interface PageContainerProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}

const PageContainer: React.FC<PageContainerProps> = ({
  title,
  subtitle,
  actions,
  children
}) => {
  return (
    <div>
      {/* Page Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-neutral-900">{title}</h1>
          {subtitle && (
            <p className="text-neutral-600 mt-2">{subtitle}</p>
          )}
        </div>
        {actions && <div className="flex gap-3">{actions}</div>}
      </div>
      
      {/* Page Content */}
      <div>{children}</div>
    </div>
  );
};
```

### State Management Architecture

**Approach**: React Context + Custom Hooks (no Redux/Zustand needed for MVP).

#### AuthContext

**Purpose**: Global authentication state.

```typescript
interface AuthContextValue {
  user: User | null;
  tenant: Tenant | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

// Usage in components:
const { user, isAuthenticated, logout } = useAuth();
```

#### FeatureFlagContext

**Purpose**: Feature flag checking.

```typescript
interface FeatureFlagContextValue {
  hasFeature: (feature: string) => boolean;
  subscription: {
    plan: string;
    features: string[];
  };
}

// Usage:
const { hasFeature } = useFeatureFlag();
if (hasFeature('recommendations')) {
  // Show recommendations section
}
```

### API Client Architecture

**Implementation**: Axios with interceptors.

**File**: `src/api/client.ts`

```typescript
import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://alpmark-production.up.railway.app';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
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
      // Token expired - logout
      localStorage.removeItem('alpmark_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

**Domain API Files**: Each domain has its own file (e.g., `src/api/executive.ts`):

```typescript
import apiClient from './client';
import type { ExecutiveDashboard, KPISummary } from './types';

export const executiveApi = {
  getDashboard: () => 
    apiClient.get<ExecutiveDashboard>('/api/v1/executive/dashboard'),
  
  getKPIs: () => 
    apiClient.get<KPISummary>('/api/v1/executive/kpis'),
  
  getMetricHistory: (metricName: string, days: number) =>
    apiClient.get(`/api/v1/executive/metrics/${metricName}/history`, {
      params: { days }
    }),
};
```

### Custom Hooks Patterns

#### useApi Hook

**Purpose**: Consistent API calling with loading/error states.

```typescript
import { useState, useEffect } from 'react';

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useApi<T>(
  apiCall: () => Promise<{ data: T }>
): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiCall();
      setData(response.data);
    } catch (err: any) {
      setError(err.response?.data?.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchData();
  }, []);
  
  return { data, loading, error, refetch: fetchData };
}

// Usage:
const { data: kpis, loading, error, refetch } = useApi(() => executiveApi.getKPIs());
```

### Error Handling Patterns

**Principle**: Always show user-friendly error messages with context.

**API Error Display**:
```tsx
{error && (
  <div className="bg-danger-50 border border-danger-200 rounded-md p-4 mb-6">
    <div className="flex items-center gap-2">
      <ExclamationTriangleIcon className="w-5 h-5 text-danger-600" />
      <h3 className="text-sm font-semibold text-danger-900">
        Failed to load data
      </h3>
    </div>
    <p className="text-sm text-danger-700 mt-1">{error}</p>
    <Button 
      variant="ghost" 
      size="sm" 
      onClick={refetch}
      className="mt-3"
    >
      Try again
    </Button>
  </div>
)}
```

**Form Validation Error Display**:
```tsx
{errors.email && (
  <p className="text-sm text-danger-600 mt-1">
    {errors.email.message}
  </p>
)}
```

### Loading State Patterns

**Skeleton Loading** (preferred):
```tsx
const KPICardSkeleton = () => (
  <div className="bg-white p-6 rounded-lg shadow-sm border border-neutral-200 animate-pulse">
    <div className="h-4 bg-neutral-200 rounded w-1/2 mb-3"></div>
    <div className="h-8 bg-neutral-200 rounded w-3/4 mb-2"></div>
    <div className="h-4 bg-neutral-200 rounded w-1/3"></div>
  </div>
);
```

**Spinner Loading** (use sparingly):
```tsx
const LoadingSpinner = () => (
  <div className="flex items-center justify-center py-12">
    <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
  </div>
);
```

### Form Handling Pattern

**Use React Hook Form**:
```tsx
import { useForm } from 'react-hook-form';

interface LoginFormData {
  email: string;
  password: string;
}

const LoginPage = () => {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginFormData>();
  const { login } = useAuth();
  
  const onSubmit = async (data: LoginFormData) => {
    try {
      await login(data.email, data.password);
    } catch (error) {
      // Error handled by AuthContext
    }
  };
  
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-1">
          Email
        </label>
        <input
          type="email"
          {...register('email', { 
            required: 'Email is required',
            pattern: {
              value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
              message: 'Invalid email address'
            }
          })}
          className="w-full px-4 py-2 border border-neutral-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        />
        {errors.email && (
          <p className="text-sm text-danger-600 mt-1">{errors.email.message}</p>
        )}
      </div>
      
      <Button type="submit" fullWidth loading={isSubmitting}>
        Sign In
      </Button>
    </form>
  );
};
```

### Accessibility Standards

**Required Practices**:

1. **Semantic HTML**: Use proper heading hierarchy (h1 → h2 → h3), button elements, nav elements
2. **Keyboard Navigation**: All interactive elements must be keyboard accessible
3. **ARIA Labels**: Add aria-label to icon buttons, aria-describedby for help text
4. **Focus Management**: Visible focus indicators (ring-2 ring-primary-500)
5. **Color Contrast**: WCAG AA compliance (4.5:1 for text, 3:1 for UI components)
6. **Alt Text**: All images must have descriptive alt attributes

**Example**:
```tsx
<button
  aria-label="Close modal"
  className="focus:outline-none focus:ring-2 focus:ring-primary-500"
  onClick={onClose}
>
  <XMarkIcon className="w-5 h-5" />
</button>
```

### Responsive Design Rules

**Breakpoints** (Tailwind default):
```
sm: 640px   (tablets)
md: 768px   (small laptops)
lg: 1024px  (desktops)
xl: 1280px  (large desktops)
```

**Layout Rules**:
- Mobile-first approach
- KPI cards: 1 column on mobile, 2 on tablet, 3-4 on desktop
- Charts: Full width on mobile, side-by-side on desktop
- Tables: Horizontal scroll on mobile, full table on desktop
- Sidebar: Hidden on mobile (hamburger menu), fixed on desktop

**Example**:
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {kpis.map(kpi => <KPICard key={kpi.name} {...kpi} />)}
</div>
```

### Chart Configuration Standards

**Use Recharts** with consistent styling:

```tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const RevenueChart = ({ data }) => (
  <ResponsiveContainer width="100%" height={320}>
    <LineChart data={data}>
      <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
      <XAxis 
        dataKey="date" 
        stroke="#71717a"
        style={{ fontSize: '12px' }}
      />
      <YAxis 
        stroke="#71717a"
        style={{ fontSize: '12px' }}
        tickFormatter={(value) => `$${formatNumber(value)}`}
      />
      <Tooltip 
        contentStyle={{
          backgroundColor: '#ffffff',
          border: '1px solid #e4e4e7',
          borderRadius: '6px',
        }}
      />
      <Line 
        type="monotone" 
        dataKey="revenue" 
        stroke="#0ea5e9" 
        strokeWidth={2}
        dot={{ fill: '#0ea5e9', r: 4 }}
        activeDot={{ r: 6 }}
      />
    </LineChart>
  </ResponsiveContainer>
);
```

**Chart Color Palette**:
```typescript
const chartColors = {
  primary: '#0ea5e9',    // Blue - primary metric
  success: '#22c55e',    // Green - positive/revenue
  warning: '#f59e0b',    // Amber - warning/attention
  danger: '#ef4444',     // Red - negative/costs
  purple: '#a855f7',     // Purple - secondary metric
  gray: '#71717a',       // Gray - baseline/comparison
};
```

---

## Backend API Reference

**Base URL**: `https://alpmark-production.up.railway.app` (or your Railway domain)

**Authentication**: All endpoints except `/api/auth/login` require JWT in `Authorization: Bearer <token>` header

### Domain 1: System & Health

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/health` | No | `{"status": "healthy"}` | Health check |
| GET | `/api/health` | No | Health details | Detailed health |

### Domain 2: Authentication

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| POST | `/api/auth/login` | No | `{access_token, user}` | Login with email/password |
| POST | `/api/auth/password-reset-request` | No | `{message}` | Request password reset |
| POST | `/api/auth/password-reset` | No | `{message}` | Reset password with token |
| GET | `/api/auth/me` | Yes | User object | Get current user |

**Login Request**:
```json
{
  "email": "owner@one8.com",
  "password": "password123"
}
```

**Login Response**:
```json
{
  "access_token": "eyJ...",
  "user": {
    "id": "uuid",
    "email": "owner@one8.com",
    "full_name": "One8 Owner",
    "platform_role": "executive_owner",
    "tenant_id": "11111111-1111-4111-8111-111111111111"
  }
}
```

### Domain 3: Tenants

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/tenants` | Super Admin | List of tenants | List all tenants |
| POST | `/api/tenants` | Super Admin | Tenant object | Create tenant |
| GET | `/api/tenants/{tenant_id}` | Super Admin | Tenant object | Get tenant details |
| PUT | `/api/tenants/{tenant_id}` | Super Admin | Tenant object | Update tenant |
| DELETE | `/api/tenants/{tenant_id}` | Super Admin | `{message}` | Delete tenant |

### Domain 4: Users

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/users` | Brand Admin | List of users | List tenant users |
| POST | `/api/users/invite` | Executive Owner / Brand Admin | Invitation object | Invite user |
| GET | `/api/users/{user_id}` | Brand Admin | User object | Get user details |
| PUT | `/api/users/{user_id}` | Brand Admin | User object | Update user |
| DELETE | `/api/users/{user_id}` | Brand Admin | `{message}` | Delete user |
| GET | `/api/users/invitations` | Brand Admin | List of invitations | List pending invitations |

### Domain 5: Subscriptions & Billing

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/subscriptions/current` | Executive Owner / Brand Admin | Subscription object | Get current subscription |
| GET | `/api/subscriptions/plans` | Any | List of plans | List available plans |
| PUT | `/api/subscriptions/upgrade` | Brand Admin | Subscription object | Upgrade plan |

### Domain 6: Integrations (Connectors)

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/integrations` | Brand Admin | List of integrations | List tenant integrations |
| POST | `/api/integrations` | Brand Admin | Integration object | Create integration |
| GET | `/api/integrations/{integration_id}` | Brand Admin | Integration object | Get integration details |
| PUT | `/api/integrations/{integration_id}` | Brand Admin | Integration object | Update integration |
| DELETE | `/api/integrations/{integration_id}` | Brand Admin | `{message}` | Delete integration |
| POST | `/api/integrations/{integration_id}/sync` | Brand Admin | Sync result | Trigger manual sync |
| GET | `/api/integrations/{integration_id}/health` | Brand Admin | Health status | Get integration health |

### Domain 7: Executive KPIs

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/executive/revenue` | Executive Owner | Revenue KPI | Get revenue metrics |
| GET | `/api/executive/profit` | Executive Owner | Profit KPI | Get profit metrics |
| GET | `/api/executive/contribution-margin` | Executive Owner | Margin KPI | Get contribution margin |
| GET | `/api/executive/growth-rate` | Executive Owner | Growth KPI | Get growth rate |
| GET | `/api/executive/cross-team-summary` | Executive Owner | Summary object | Get cross-team rollup |
| GET | `/api/executive/business-health` | Executive Owner | Chart data | Get business health chart |
| GET | `/api/executive/alerts` | Executive Owner | List of alerts | Get priority alerts |

**Example Response** (`/api/executive/revenue`):
```json
{
  "current_value": 10000000.00,
  "previous_value": 9500000.00,
  "percentage_change": 5.26,
  "trend": "up",
  "confidence": 87,
  "confidence_label": "High",
  "last_updated": "2026-06-20T09:20:00Z",
  "data_sources": ["Shopify", "Manual Input"],
  "formula": "Sum of all order revenues - refunds",
  "definition": "Total revenue from product sales after refunds"
}
```

### Domain 8: Growth (Acquisition & Marketing)

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/growth/marketing-spend` | Growth Manager | Spend KPI | Marketing spend metrics |
| GET | `/api/growth/roas` | Growth Manager | ROAS KPI | Return on ad spend |
| GET | `/api/growth/cac` | Growth Manager | CAC KPI | Customer acquisition cost |
| GET | `/api/growth/payback-period` | Growth Manager | Payback KPI | CAC payback period |
| GET | `/api/growth/channel-performance` | Growth Manager | Chart data | Channel performance chart |
| GET | `/api/growth/campaigns` | Growth Manager | Campaign table | Campaign performance table |
| GET | `/api/growth/spend-by-channel` | Growth Manager | Chart data | Spend breakdown |
| GET | `/api/growth/roas-trend` | Growth Manager | Chart data | ROAS over time |
| GET | `/api/growth/cac-trend` | Growth Manager | Chart data | CAC over time |

### Domain 9: Retention & CRM

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/retention/retention-rate` | Retention Manager | Retention KPI | Retention rate |
| GET | `/api/retention/repeat-purchase-rate` | Retention Manager | RPR KPI | Repeat purchase rate |
| GET | `/api/retention/customer-lifetime-value` | Retention Manager | CLV KPI | Customer lifetime value |
| GET | `/api/retention/churn-risk` | Retention Manager | Churn KPI | Churn risk score |
| GET | `/api/retention/cohort-analysis` | Retention Manager | Heatmap data | Monthly cohort heatmap |
| GET | `/api/retention/lifecycle-funnel` | Retention Manager | Funnel data | Lifecycle funnel |
| GET | `/api/retention/segments` | Retention Manager | List of segments | Customer segments |

**Segments** (predefined):
- New Customers
- Returning Customers
- High Value Customers
- At Risk Customers
- Churned Customers
- Custom Segments (user-created)

### Domain 10: Finance

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/finance/contribution-margin` | Finance Controller | Margin KPI | Contribution margin |
| GET | `/api/finance/gross-profit` | Finance Controller | Profit KPI | Gross profit |
| GET | `/api/finance/net-profit` | Finance Controller | Profit KPI | Net profit |
| GET | `/api/finance/cogs` | Finance Controller | COGS KPI | Cost of goods sold |
| GET | `/api/finance/contribution-margin-chart` | Finance Controller | Chart data | Margin breakdown chart |
| GET | `/api/finance/cost-breakdown` | Finance Controller | Chart data | Cost categories donut |
| GET | `/api/finance/margin-trend` | Finance Controller | Chart data | Margin over time |
| GET | `/api/finance/category-profitability` | Finance Controller | Chart data | Profitability by category |
| GET | `/api/finance/cost-drivers` | Finance Controller | List of costs | Detailed cost entries |

**Cost Entry** includes:
- Source (synced or manual)
- Owner
- Last updated
- Confidence score

### Domain 11: Operations & Inventory

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/operations/in-stock` | Operations Manager | Stock KPI | In-stock count |
| GET | `/api/operations/low-stock` | Operations Manager | Stock KPI | Low stock count |
| GET | `/api/operations/stockout-risk` | Operations Manager | Risk KPI | Stockout risk items |
| GET | `/api/operations/slow-moving` | Operations Manager | Slow-move KPI | Slow moving inventory |
| GET | `/api/operations/inventory-value` | Operations Manager | Value KPI | Total inventory value |
| GET | `/api/operations/inventory-distribution` | Operations Manager | Treemap data | Inventory by category/warehouse |
| GET | `/api/operations/warehouse-heatmap` | Operations Manager | Heatmap data | Warehouse distribution |
| GET | `/api/operations/returns-analysis` | Operations Manager | Pareto data | Top return items |
| GET | `/api/operations/stockout-trend` | Operations Manager | Chart data | Stockout trend |

### Domain 12: Recommendations

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/recommendations` | Executive Owner + Dept Users | List of recommendations | Get active recommendations |
| GET | `/api/recommendations/{rec_id}` | Executive Owner + Dept Users | Recommendation object | Get recommendation details |
| PUT | `/api/recommendations/{rec_id}/review` | Executive Owner + Dept Users | Recommendation object | Mark as reviewed |
| PUT | `/api/recommendations/{rec_id}/dismiss` | Executive Owner + Dept Users | Recommendation object | Dismiss recommendation |
| GET | `/api/recommendations/history` | Executive Owner + Dept Users | List of recommendations | Get historical recommendations |

**Recommendation Object**:
```json
{
  "id": "uuid",
  "title": "Reduce Meta Spend by 15%",
  "summary": "Meta CAC increased 28%, ROAS dropped to 2.1",
  "why": "CAC increased: 28% | ROAS dropped: 3.2 → 2.1 | Contribution Margin reduced: 44% → 39%",
  "expected_impact": {
    "margin": "+3%",
    "revenue": "+2%"
  },
  "confidence": 87,
  "confidence_label": "High",
  "confidence_explanation": "High confidence because: 18 months of historical data, All integrations healthy, Low data volatility, Strong historical correlation",
  "data_sources": ["Meta", "Shopify", "Manual Cost Inputs"],
  "last_updated": "2026-06-20T10:00:00Z",
  "simulation_available": true,
  "status": "new",
  "category": "growth",
  "persona_target": "growth_manager",
  "created_at": "2026-06-20T08:00:00Z"
}
```

### Domain 13: Simulations

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/simulations` | Executive Owner + Dept Users | List of simulations | Get user's simulations |
| POST | `/api/simulations` | Executive Owner + Dept Users | Simulation object | Create simulation |
| GET | `/api/simulations/{sim_id}` | Executive Owner + Dept Users | Simulation object | Get simulation details |
| PUT | `/api/simulations/{sim_id}` | Executive Owner + Dept Users | Simulation object | Update simulation |
| DELETE | `/api/simulations/{sim_id}` | Executive Owner + Dept Users | `{message}` | Delete simulation |
| POST | `/api/simulations/{sim_id}/scenarios` | Executive Owner + Dept Users | Scenario object | Add scenario |
| GET | `/api/simulations/{sim_id}/compare` | Executive Owner + Dept Users | Comparison table | Compare scenarios |

**Create Simulation Request**:
```json
{
  "name": "Q3 Budget Allocation",
  "simulation_type": "budget_allocation",
  "baseline": {
    "marketing_spend": 5000000,
    "roas": 3.2,
    "margin": 42,
    "revenue": 10000000
  }
}
```

**Scenario Request**:
```json
{
  "name": "Aggressive",
  "parameters": {
    "marketing_spend": 6500000,
    "roas": 3.6,
    "margin": 39,
    "revenue": 11000000
  }
}
```

**Comparison Response**:
```json
{
  "baseline": { "revenue": 10000000, "margin": 42, "roas": 3.2, "cac": 2200 },
  "conservative": { "revenue": 9500000, "margin": 44, "roas": 3.0, "cac": 2400 },
  "aggressive": { "revenue": 11000000, "margin": 39, "roas": 3.6, "cac": 1900 }
}
```

### Domain 14: Alerts

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/alerts` | All Business Users | List of alerts | Get active alerts |
| GET | `/api/alerts/{alert_id}` | All Business Users | Alert object | Get alert details |
| PUT | `/api/alerts/{alert_id}/acknowledge` | All Business Users | Alert object | Acknowledge alert |
| PUT | `/api/alerts/{alert_id}/resolve` | All Business Users | Alert object | Resolve alert |
| GET | `/api/alerts/history` | All Business Users | List of alerts | Get alert history |

**Alert Object**:
```json
{
  "id": "uuid",
  "severity": "critical",
  "title": "Meta CAC Rising",
  "description": "Customer acquisition cost increased 28% in last 7 days",
  "trigger_point": "2026-06-18T14:30:00Z",
  "status": "active",
  "category": "growth",
  "persona_target": "growth_manager",
  "related_kpi": "cac",
  "data_sources": ["Meta"],
  "created_at": "2026-06-18T14:30:00Z"
}
```

### Domain 15: Saved Views

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/saved-views` | All Business Users | List of views | Get user's saved views |
| POST | `/api/saved-views` | All Business Users | View object | Create saved view |
| GET | `/api/saved-views/{view_id}` | All Business Users | View object | Get saved view |
| PUT | `/api/saved-views/{view_id}` | All Business Users | View object | Update saved view |
| DELETE | `/api/saved-views/{view_id}` | All Business Users | `{message}` | Delete saved view |

**Saved View** contains:
- Date filters
- Dashboard layout
- Pinned metrics
- Selected charts
- Custom filters
- Notes

### Domain 16: Custom Segments

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/segments` | Retention Manager | List of segments | Get segments |
| POST | `/api/segments` | Retention Manager | Segment object | Create custom segment |
| GET | `/api/segments/{segment_id}` | Retention Manager | Segment object | Get segment details |
| PUT | `/api/segments/{segment_id}` | Retention Manager | Segment object | Update segment |
| DELETE | `/api/segments/{segment_id}` | Retention Manager | `{message}` | Delete segment |
| GET | `/api/segments/{segment_id}/customers` | Retention Manager | List of customers | Get segment customers |

### Domain 17: Audit Logs

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/audit-logs` | Brand Admin | List of logs | Get audit logs |
| GET | `/api/audit-logs/{log_id}` | Brand Admin | Log object | Get log details |

**Audit Log Entry**:
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "user_email": "admin@one8.com",
  "action": "user.invite",
  "resource_type": "user",
  "resource_id": "uuid",
  "details": {"email": "newuser@one8.com", "role": "growth_manager"},
  "ip_address": "203.0.113.1",
  "created_at": "2026-06-20T10:00:00Z"
}
```

### Domain 18: Workspace Health

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/workspace/health` | Brand Admin | Health summary | Get workspace health |
| GET | `/api/workspace/seat-usage` | Brand Admin | Seat usage data | Get seat usage |
| GET | `/api/workspace/integration-health` | Brand Admin | Integration health | Get integration status |
| GET | `/api/workspace/data-freshness` | Brand Admin | Freshness status | Get data freshness |

**Workspace Health Response**:
```json
{
  "users_configured": 8,
  "seat_limit": 10,
  "integrations_healthy": 4,
  "integrations_total": 5,
  "data_freshness": "good",
  "recommendations_active": 12,
  "simulations_enabled": true,
  "sync_errors": 1,
  "billing_status": "active"
}
```

### Domain 19: Feature Flags

| Method | Path | Auth | Response | Purpose |
|--------|------|------|----------|---------|
| GET | `/api/features` | All Users | Feature map | Get available features for current tenant |

**Feature Map Response**:
```json
{
  "recommendations": true,
  "simulations": true,
  "custom_segments": true,
  "saved_views": true,
  "exports": true,
  "excel_upload": true,
  "custom_roles": false,
  "google_ads_connector": false,
  "erp_connector": false
}
```

Use this endpoint to conditionally render UI elements based on tenant's subscription plan.

---

## Authentication & Identity

### Login Flow

**Frontend Flow**:
1. User visits `/login`
2. User enters email + password
3. POST `/api/auth/login`
4. Receive `{access_token, user}`
5. Store token in localStorage/sessionStorage
6. Store user object in state/context
7. Add token to all subsequent requests: `Authorization: Bearer <token>`
8. Redirect based on `user.platform_role`:
   - `super_admin` → `/admin/dashboard`
   - `executive_owner` → `/executive/home`
   - `growth_manager` → `/growth/home`
   - `retention_manager` → `/retention/home`
   - `finance_controller` → `/finance/home`
   - `operations_manager` → `/operations/home`
   - `brand_admin` → `/admin/home`
   - `support_operator` → `/support/dashboard`

### Demo Login Credentials

**Tenant**: one8  
**Tenant ID**: `11111111-1111-4111-8111-111111111111`

**Users**:
- **Executive Owner**: `owner@one8.com` / `password123`
- **Brand Admin**: `admin@one8.com` / `password123`
- **Growth Manager**: `growth@one8.com` / `password123`
- **Retention Manager**: `retention@one8.com` / `password123`
- **Finance Controller**: `finance@one8.com` / `password123`
- **Operations Manager**: `ops@one8.com` / `password123`

### Token Management

**Token contains**:
```json
{
  "sub": "owner@one8.com",
  "email": "owner@one8.com",
  "platform_role": "executive_owner",
  "exp": 1719821234
}
```

**Refresh Strategy**:
- Check token expiration on app load
- If expired, redirect to `/login`
- If valid, fetch user via `GET /api/auth/me` to verify token still valid

### Protected Routes

Create a route guard that checks:
1. Token exists
2. Token not expired
3. User has required role for route

Example role requirements:
- `/executive/*` → `executive_owner`
- `/growth/*` → `growth_manager`
- `/retention/*` → `retention_manager`
- `/finance/*` → `finance_controller`
- `/operations/*` → `operations_manager`
- `/admin/*` → `brand_admin`
- `/admin/platform/*` → `super_admin`
- `/support/*` → `support_operator`

---

## Persona Dashboard Specifications

### PER-01: Executive Owner

**Purpose**: Highest business authority. Needs high-level view of entire business.

**Homepage Layout**:

**Row 1 - Top KPIs** (4 cards):
- Revenue: `GET /api/executive/revenue`
- Profit: `GET /api/executive/profit`
- Contribution Margin: `GET /api/executive/contribution-margin`
- Growth Rate: `GET /api/executive/growth-rate`

**Row 2 - Business Health Chart** (full width):
- Combined revenue + profit + margin over time
- `GET /api/executive/business-health`
- Line chart with 3 lines, current period + previous period comparison

**Row 3 - Priority Alerts** (full width):
- `GET /api/executive/alerts`
- Display top 5 critical/high alerts
- Examples: "Meta CAC rising", "Margin declining", "Inventory shortage risk"

**Row 4 - Strategic Recommendations** (full width):
- `GET /api/recommendations?persona=executive_owner&status=new`
- Display top 5 recommendations
- Show: title, summary, expected impact, confidence, simulation button

**Row 5 - Cross-Team Rollup** (4 cards):
- `GET /api/executive/cross-team-summary`
- Growth: Healthy/Risk/Critical
- Retention: Healthy/Risk/Critical
- Finance: Healthy/Risk/Critical
- Operations: Healthy/Risk/Critical

**Sidebar Navigation**:
- Home
- Analytics (all departments)
- Recommendations
- Simulations
- Saved Views
- Reports

**Permissions**:
- ✓ View all business dashboards
- ✓ View recommendations
- ✓ Run simulations
- ✓ Pin KPIs
- ✓ Customize homepage
- ✗ Manage billing
- ✗ Configure integrations
- ✗ Manage users

---

### PER-02: Growth & Performance Manager

**Purpose**: Optimize customer acquisition and marketing performance.

**Homepage Layout**:

**Row 1 - Top KPIs** (5 cards):
- Marketing Spend: `GET /api/growth/marketing-spend`
- ROAS: `GET /api/growth/roas`
- CAC: `GET /api/growth/cac`
- Payback Period: `GET /api/growth/payback-period`
- Contribution Margin: `GET /api/executive/contribution-margin`

**Row 2 - Channel Performance Chart** (full width, 60% of page):
- `GET /api/growth/channel-performance`
- Bubble chart: X=Spend, Y=Margin, Bubble Size=Revenue
- Interactive: click to drill down

**Row 3 - Charts** (2 columns):
- Left: Spend by Channel (stacked bar) - `GET /api/growth/spend-by-channel`
- Right: ROAS Trend (line) - `GET /api/growth/roas-trend`

**Row 4 - Campaign Performance Table**:
- `GET /api/growth/campaigns`
- Columns: Campaign, Spend, Revenue, ROAS, CAC, Contribution Margin, Trend
- Sortable, filterable
- Max 10 rows, pagination

**Sidebar Navigation**:
- Home
- Analytics
- Recommendations
- Simulations
- Saved Views
- Exports

**Can Simulate**:
- Budget Allocation
- CAC Changes
- ROAS Changes
- Channel Mix
- Customer Growth

**Permissions**:
- ✓ View growth dashboards
- ✓ View recommendations (growth category)
- ✓ Run simulations (growth related)
- ✗ View finance details
- ✗ View operations
- ✗ Manage users
- ✗ Manage billing

---

### PER-03: Retention & CRM Manager

**Purpose**: Improve customer loyalty, repeat purchases, reduce churn.

**Homepage Layout**:

**Row 1 - Top KPIs** (5 cards):
- Retention Rate: `GET /api/retention/retention-rate`
- Repeat Purchase Rate: `GET /api/retention/repeat-purchase-rate`
- Customer Lifetime Value: `GET /api/retention/customer-lifetime-value`
- Churn Risk: `GET /api/retention/churn-risk`
- Average Order Value: `GET /api/executive/aov`

**Row 2 - Cohort Analysis Heatmap** (full width):
- `GET /api/retention/cohort-analysis`
- Monthly cohorts on Y-axis, months on X-axis
- Color intensity = retention %
- Show customer counts on hover

**Row 3 - Charts** (2 columns):
- Left: Lifecycle Funnel - `GET /api/retention/lifecycle-funnel`
- Right: Customer Segments (donut) - `GET /api/retention/segments`

**Row 4 - Churn Trend** (full width):
- `GET /api/retention/churn-trend`
- Line chart showing churn rate over time

**Row 5 - Customer Segments**:
- `GET /api/retention/segments`
- Tabs: New Customers, Returning, High Value, At Risk, Churned, Custom
- Click segment → drill down to customer list

**Sidebar Navigation**:
- Home
- Cohort Analysis
- Segments
- Recommendations
- Simulations
- Campaigns

**Can Simulate**:
- Discount Levels
- Campaign Timing
- Segment Sizes
- Retention Strategies

**Permissions**:
- ✓ View retention dashboards
- ✓ Create custom segments
- ✓ View recommendations (retention category)
- ✓ Run simulations (retention related)
- ✗ Access finance
- ✗ Manage integrations
- ✗ Manage users

---

### PER-04: Finance Controller

**Purpose**: Manage profitability, margins, costs, variance.

**Homepage Layout**:

**Row 1 - Top KPIs** (4 cards):
- Contribution Margin: `GET /api/finance/contribution-margin`
- Gross Profit: `GET /api/finance/gross-profit`
- Net Profit: `GET /api/finance/net-profit`
- COGS: `GET /api/finance/cogs`

**Row 2 - Contribution Margin Chart** (full width):
- `GET /api/finance/contribution-margin-chart`
- Stacked area chart: Revenue, Marketing, COGS, Shipping, Returns, Margin

**Row 3 - Charts** (2 columns):
- Left: Cost Breakdown (donut) - `GET /api/finance/cost-breakdown`
- Right: Margin Trend (line) - `GET /api/finance/margin-trend`

**Row 4 - Category Profitability**:
- `GET /api/finance/category-profitability`
- Horizontal bar chart showing margin by product category

**Row 5 - Cost Drivers Table**:
- `GET /api/finance/cost-drivers`
- Columns: Cost Item, Amount, Source (Synced/Manual), Owner, Last Updated, Confidence
- Every entry shows data provenance

**Sidebar Navigation**:
- Home
- Margins
- Costs
- Recommendations
- Simulations
- Reports

**Can Simulate**:
- Shipping Costs
- Tax Changes
- Discount Rates
- Platform Fees
- Return Costs

**Permissions**:
- ✓ View finance dashboards
- ✓ View all cost data
- ✓ View recommendations (finance category)
- ✓ Run simulations (finance related)
- ✗ Manage users
- ✗ Manage integrations
- ✗ Manage billing

---

### PER-05: Operations & Inventory Manager

**Purpose**: Maintain inventory health, reduce stockouts, optimize warehouse efficiency.

**Homepage Layout**:

**Row 1 - Top KPIs** (5 cards):
- In Stock: `GET /api/operations/in-stock`
- Low Stock: `GET /api/operations/low-stock`
- Stockout Risk: `GET /api/operations/stockout-risk`
- Slow Moving: `GET /api/operations/slow-moving`
- Inventory Value: `GET /api/operations/inventory-value`

**Row 2 - Inventory Distribution Treemap** (full width):
- `GET /api/operations/inventory-distribution`
- Treemap showing categories, warehouses, stock concentration
- Size = inventory value, color = stock health

**Row 3 - Charts** (2 columns):
- Left: Warehouse Heatmap - `GET /api/operations/warehouse-heatmap`
- Right: Returns Analysis (Pareto) - `GET /api/operations/returns-analysis`

**Row 4 - Stockout Trend**:
- `GET /api/operations/stockout-trend`
- Line chart showing stockout incidents over time

**Sidebar Navigation**:
- Home
- Inventory
- Warehouses
- Returns
- Recommendations
- Simulations

**Can Simulate**:
- Lead Time
- Demand Changes
- Shipping Costs
- Reorder Quantity

**Permissions**:
- ✓ View operations dashboards
- ✓ View inventory data
- ✓ View recommendations (operations category)
- ✓ Run simulations (operations related)
- ✗ Manage users
- ✗ Manage billing
- ✗ Manage integrations

---

### PER-06: Brand Admin

**Purpose**: Configure AlpMark workspace. Does NOT consume business intelligence.

**Homepage**:

If onboarding incomplete:
- Display **Onboarding Checklist**
- Connect Shopify ✓
- Connect Meta Ads ⏳
- Connect Google Ads ⏳
- Invite Other Members of the Team
- Assign Roles
- Complete Initial Sync ✓
- Review First KPIs
- Review First Recommendations

If onboarding complete:
- Display **Workspace Health** dashboard

**Workspace Health**:
- Users Configured: 8 / 10
- Integrations Healthy: 4 / 5
- Data Freshness: Good
- Recommendations: Active
- Simulations: Enabled
- Sync Errors: 1
- Seat Usage: 7 / 10

**Charts**:
- User Growth (line chart)
- Integration Health (donut chart)
- Seat Usage (progress chart)

**Sidebar Navigation**:
- Home
- Users
- Roles
- Integrations
- Billing
- Audit Logs
- Workspace Health

**Features**:
- ✓ Invite users: `POST /api/users/invite`
- ✓ Assign roles: `PUT /api/users/{user_id}`
- ✓ Manage integrations: `GET/POST/PUT/DELETE /api/integrations/*`
- ✓ View billing: `GET /api/subscriptions/current`
- ✓ Review audit logs: `GET /api/audit-logs`
- ✓ Manage seats

**Cannot Access**:
- ✗ Recommendations
- ✗ Simulations
- ✗ Business dashboards
- ✗ Analytics

---

### PER-07: AlpMark Super Admin

**Purpose**: Manage AlpMark platform globally. AlpMark employee.

**Homepage**:

**Row 1 - Platform KPIs** (5 cards):
- Total Tenants: `GET /api/tenants` → count
- MRR: `GET /api/admin/mrr`
- Support Tickets: `GET /api/admin/tickets`
- Active Users: `GET /api/admin/active-users`
- Platform Health: `GET /api/admin/health`

**Row 2 - Charts** (2 columns):
- Left: Tenant Growth (line) - `GET /api/admin/tenant-growth`
- Right: Subscription Distribution (donut) - `GET /api/admin/subscription-distribution`

**Row 3 - Platform Health Timeline**:
- `GET /api/admin/health-timeline`
- Timeline showing system incidents, upgrades, maintenance

**Row 4 - Support Tickets**:
- `GET /api/admin/tickets`
- Bar chart showing tickets by priority

**Sidebar Navigation**:
- Dashboard
- Tenants
- Subscription Plans
- Feature Toggles
- Platform Health
- Billing
- Support

**Features**:
- ✓ Create tenant: `POST /api/tenants`
- ✓ Suspend tenant: `PUT /api/tenants/{id}`
- ✓ Manage plans: `GET/POST/PUT /api/admin/plans`
- ✓ Feature toggles: Enable/disable features per tenant
- ✓ Monitor platform: System health, errors, performance
- ✓ Manage billing: View all subscriptions

**Feature Toggles Control**:
- Recommendations: ON/OFF
- Simulations: ON/OFF
- Excel Upload: ON/OFF
- Saved Views: ON/OFF
- Custom Roles: ON/OFF
- Connectors: Google Ads, SAP, etc.
- Exports: ON/OFF

**Cannot Access**:
- ✗ Customer business data
- ✗ Customer recommendations
- ✗ Customer simulations

---

### PER-08: Support Operator

**Purpose**: Help customers troubleshoot issues. Read-only access.

**Homepage**:

**Row 1 - Support KPIs**:
- Assigned Tickets
- Escalations
- Sync Failures
- Connector Health
- Recent Activity

**Row 2 - Charts** (3 columns):
- Ticket Volume (line)
- Connector Health (donut)
- Integration Failures (bar)

**Row 3 - Ticket Queue**:
- `GET /api/support/tickets`
- Columns: Tenant, Priority, Status, Assigned To, Due Date
- Click → ticket details

**Sidebar Navigation**:
- Dashboard
- Tickets
- Tenants
- Connector Health

**Features**:
- ✓ View tenant details: `GET /api/tenants/{id}`
- ✓ View users: `GET /api/users?tenant_id={id}`
- ✓ View integrations: `GET /api/integrations?tenant_id={id}`
- ✓ View audit logs: `GET /api/audit-logs?tenant_id={id}`
- ✓ Resolve tickets: `PUT /api/support/tickets/{id}/resolve`

**Cannot Access**:
- ✗ Business analytics
- ✗ Recommendations
- ✗ Simulations
- ✗ Billing controls
- ✗ User management

---

## Supporting Systems

### Recommendation Framework

**Core Principle**: Recommendations are intelligence, not commands.

**Every Recommendation Must Show**:
1. **What happened?** - Summary of the situation
2. **Why did AlpMark generate this?** - Signals that triggered it
3. **What data was used?** - Data sources (✓ Shopify, ✓ Meta)
4. **How confident is AlpMark?** - Confidence score (87%, "High")
5. **What is the expected impact?** - Margin +3%, Revenue +2%
6. **Can this be simulated?** - Yes/No + button

**Recommendation Card Component**:
```jsx
<RecommendationCard>
  <Title>Reduce Meta Spend by 15%</Title>
  <Summary>Meta CAC increased 28%, ROAS dropped to 2.1</Summary>
  
  <Why>
    <Metric>CAC increased: 28%</Metric>
    <Metric>ROAS dropped: 3.2 → 2.1</Metric>
    <Metric>Contribution Margin reduced: 44% → 39%</Metric>
  </Why>
  
  <ExpectedImpact>
    <Impact label="Margin">+3%</Impact>
    <Impact label="Revenue">+2%</Impact>
  </ExpectedImpact>
  
  <Confidence score={87} label="High">
    High confidence because: 18 months of historical data, 
    All integrations healthy, Low data volatility
  </Confidence>
  
  <Actions>
    <Button>Simulate</Button>
    <Button>Review</Button>
    <Button>Dismiss</Button>
  </Actions>
</RecommendationCard>
```

**Recommendation Lifecycle**:
- **Generated**: Backend creates recommendation
- **Reviewed**: User opens recommendation details
- **Dismissed**: User decides not relevant
- **Expired**: Conditions changed, no longer valid
- **Archived**: Historical reference

---

### Simulation Framework

**Core Principle**: Simulations are business sandboxes, not calculators.

**Every Simulation Begins With Baseline**:
- Baseline = current business state
- User creates: Conservative, Aggressive, Custom scenarios
- Compare side-by-side

**Scenario Comparison Component**:
```jsx
<SimulationComparison>
  <Table>
    <thead>
      <tr>
        <th>Metric</th>
        <th>Baseline</th>
        <th>Conservative</th>
        <th>Aggressive</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Revenue</td>
        <td>₹10 Cr</td>
        <td className="text-orange">₹9.5 Cr</td>
        <td className="text-green">₹11 Cr</td>
      </tr>
      <tr>
        <td>Margin</td>
        <td>42%</td>
        <td className="text-green">44%</td>
        <td className="text-orange">40%</td>
      </tr>
      <tr>
        <td>ROAS</td>
        <td>3.2</td>
        <td className="text-orange">3.0</td>
        <td className="text-green">3.6</td>
      </tr>
    </tbody>
  </Table>
</SimulationComparison>
```

**Visual Highlighting**:
- Positive change: Green
- Negative change: Red
- Neutral: Gray

**Simulation Actions**:
- Create Scenario
- Duplicate Scenario
- Rename Scenario
- Delete Scenario
- Export Scenario
- Save Scenario

---

### Explainability Framework

**Core Principle**: Nothing in AlpMark should feel like a black box.

**KPI Explainability Modal**:
```jsx
<ExplainabilityModal kpi="contribution_margin">
  <Section title="Definition">
    Contribution Margin measures the profitability remaining 
    after variable business costs have been deducted.
  </Section>
  
  <Section title="Formula">
    (Net Revenue - COGS - Shipping - Marketing - Returns) / Net Revenue
  </Section>
  
  <Section title="Data Sources">
    ✓ Shopify
    ✓ Meta
    ✓ Manual Cost Inputs
  </Section>
  
  <Section title="Last Updated">
    18 June 2026, 09:42 UTC
  </Section>
  
  <Section title="Confidence">
    87% - High
    
    High confidence because:
    • 18 months of historical data
    • All integrations healthy
    • Low data volatility
    • Strong historical correlation
  </Section>
</ExplainabilityModal>
```

**Trigger**: Every KPI card has small info icon (ⓘ) → click → modal

---

### Data Freshness

**Core Principle**: Users must always know how fresh their data is.

**Freshness States**:
- **Fresh**: Data within acceptable limits (green)
- **Delayed**: Data older than expected (yellow)
- **Critical**: Data significantly outdated (red)
- **Unknown**: Cannot determine freshness (gray)

**Display Freshness**:
- On every KPI card: "Last updated: 18 June 2026, 09:42 UTC"
- On connector health: "Last synced: 2 hours ago"
- On integration list: Visual health indicator

**Stale Data Warning**:
If data > 24 hours old, show banner:
"⚠️ Some data is more than 24 hours old. Results may not reflect recent changes. Last sync: 18 June 2026."

---

### Confidence Scores

**Core Principle**: Always show how confident AlpMark is.

**Confidence Levels**:
- **90-100%**: Very High (dark green)
- **75-89%**: High (green)
- **60-74%**: Medium (yellow)
- **40-59%**: Low (orange)
- **0-39%**: Very Low (red)

**Confidence Factors**:
- Historical data availability
- Data freshness
- Integration health
- Historical volatility
- Model reliability

**Display**:
```jsx
<Confidence score={87} label="High">
  <ProgressBar value={87} color="green" />
  <Label>High</Label>
  <Tooltip>
    High confidence because:
    • 18 months of historical data
    • All integrations healthy
    • Low data volatility
  </Tooltip>
</Confidence>
```

---

## Data Models & Relationships

### Core Entities

**Tenant**:
```typescript
interface Tenant {
  id: string;
  name: string;
  subscription_plan: 'Starter' | 'Growth' | 'Enterprise' | 'Custom';
  seat_limit: number;
  currency: string;
  timezone: string;
  status: 'trial' | 'active' | 'past_due' | 'suspended' | 'cancelled';
  created_at: string;
}
```

**User**:
```typescript
interface User {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  platform_role: 'super_admin' | 'executive_owner' | 'brand_admin' | 
                 'growth_manager' | 'retention_manager' | 'finance_controller' | 
                 'operations_manager' | 'support_operator';
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}
```

**Integration**:
```typescript
interface Integration {
  id: string;
  tenant_id: string;
  connector_type: 'shopify' | 'meta' | 'google_ads' | 'excel' | 'erp' | 'crm';
  status: 'healthy' | 'warning' | 'failed' | 'disabled';
  last_synced_at: string | null;
  records_imported: number;
  sync_duration_seconds: number | null;
  error_message: string | null;
  config: Record<string, any>;
  created_at: string;
}
```

**Recommendation**:
```typescript
interface Recommendation {
  id: string;
  tenant_id: string;
  title: string;
  summary: string;
  why: string;
  expected_impact: {
    margin?: string;
    revenue?: string;
    cac?: string;
    [key: string]: string | undefined;
  };
  confidence: number;
  confidence_label: 'Very High' | 'High' | 'Medium' | 'Low' | 'Very Low';
  confidence_explanation: string;
  data_sources: string[];
  simulation_available: boolean;
  status: 'new' | 'reviewed' | 'dismissed' | 'expired' | 'archived';
  category: 'growth' | 'retention' | 'finance' | 'operations' | 'executive';
  persona_target: string;
  created_at: string;
  last_updated: string;
}
```

**Simulation**:
```typescript
interface Simulation {
  id: string;
  tenant_id: string;
  user_id: string;
  name: string;
  simulation_type: 'budget_allocation' | 'pricing' | 'demand_forecast' | 'channel_mix';
  baseline: Record<string, number>;
  scenarios: Scenario[];
  created_at: string;
  updated_at: string;
}

interface Scenario {
  id: string;
  simulation_id: string;
  name: string;
  parameters: Record<string, number>;
  created_at: string;
}
```

**Alert**:
```typescript
interface Alert {
  id: string;
  tenant_id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  trigger_point: string;
  status: 'active' | 'acknowledged' | 'resolved';
  category: 'growth' | 'retention' | 'finance' | 'operations';
  persona_target: string;
  related_kpi: string;
  data_sources: string[];
  created_at: string;
}
```

---

## Feature Flags & Subscription Plans

### Subscription Plans

| Feature | Starter | Growth | Enterprise | Custom |
|---------|---------|--------|------------|--------|
| Max Seats | 5 | 15 | 50 | Unlimited |
| Recommendations | ✓ | ✓ | ✓ | ✓ |
| Simulations | ✗ | ✓ | ✓ | ✓ |
| Custom Segments | ✗ | ✓ | ✓ | ✓ |
| Saved Views | ✓ | ✓ | ✓ | ✓ |
| Exports | ✗ | ✓ | ✓ | ✓ |
| Excel Upload | ✓ | ✓ | ✓ | ✓ |
| Custom Roles | ✗ | ✗ | ✓ | ✓ |
| Google Ads Connector | ✗ | ✓ | ✓ | ✓ |
| ERP Connector | ✗ | ✗ | ✓ | ✓ |
| API Access | ✗ | ✗ | ✓ | ✓ |

### Frontend Feature Checking

**Always check features before rendering**:

```typescript
// Fetch features on app load
const features = await fetch('/api/features').then(r => r.json());

// Store in context
const FeaturesContext = createContext<FeatureMap>(features);

// Use in components
const { simulations, custom_segments } = useFeatures();

// Conditional rendering
{simulations && <SimulationButton />}
{custom_segments && <CustomSegmentTab />}
```

**Important**: If feature is disabled:
- Do NOT show disabled button
- Do NOT show grayed out menu item
- Component should NOT exist visually at all

### Feature Flag Architecture

**Tenant Level** (feature availability):
- Controlled by Super Admin
- Based on subscription plan
- Affects: pages, sidebar, buttons, API access

**User Level** (permissions):
- Controlled by Brand Admin
- Based on platform_role
- Affects: which features user can access within available features

**Relationship**: Tenant feature overrides user permission.

Example:
- Tenant: Simulations = DISABLED
- User: Can Use Simulations = TRUE
- Result: User CANNOT access simulations (tenant feature disabled)

---

## Step-by-Step Build Instructions

### Phase 1: Project Setup

**Step 1: Initialize React Project**

```bash
# Using Vite (recommended)
npm create vite@latest alpmark-frontend -- --template react-ts
cd alpmark-frontend
npm install

# Install core dependencies
npm install react-router-dom axios @tanstack/react-query
npm install recharts date-fns zustand
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu
npm install tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Install auth dependencies
npm install jwt-decode
```

**Step 2: Configure Tailwind**

Update `tailwind.config.js`:
```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'brand-blue': '#0066FF',
        'brand-green': '#00C853',
        'brand-red': '#FF3B30',
        'brand-yellow': '#FFCC00',
        'brand-gray': '#F5F5F7',
      },
    },
  },
  plugins: [],
}
```

**Step 3: Environment Variables**

Create `.env`:
```
VITE_API_BASE_URL=https://alpmark-production.up.railway.app
VITE_AUTH_SECRET=alpmark-dev-secret-alpmark-dev-secret-2026
```

**Step 4: Project Structure**

```
src/
├── api/              # API client and endpoints
│   ├── client.ts
│   ├── auth.ts
│   ├── executive.ts
│   ├── growth.ts
│   ├── retention.ts
│   ├── finance.ts
│   ├── operations.ts
│   ├── recommendations.ts
│   └── simulations.ts
├── components/       # Reusable components
│   ├── KPICard.tsx
│   ├── Chart.tsx
│   ├── RecommendationCard.tsx
│   ├── SimulationTable.tsx
│   ├── ExplainabilityModal.tsx
│   └── Sidebar.tsx
├── contexts/         # React contexts
│   ├── AuthContext.tsx
│   └── FeaturesContext.tsx
├── hooks/            # Custom hooks
│   ├── useAuth.ts
│   ├── useFeatures.ts
│   └── useKPI.ts
├── layouts/          # Layout components
│   ├── MainLayout.tsx
│   ├── AuthLayout.tsx
│   └── AdminLayout.tsx
├── pages/            # Page components
│   ├── auth/
│   │   ├── Login.tsx
│   │   └── PasswordReset.tsx
│   ├── executive/
│   │   └── Home.tsx
│   ├── growth/
│   │   └── Home.tsx
│   ├── retention/
│   │   └── Home.tsx
│   ├── finance/
│   │   └── Home.tsx
│   ├── operations/
│   │   └── Home.tsx
│   └── admin/
│       └── Home.tsx
├── types/            # TypeScript types
│   ├── api.ts
│   ├── user.ts
│   └── recommendation.ts
├── utils/            # Utility functions
│   ├── auth.ts
│   └── format.ts
├── App.tsx
└── main.tsx
```

---

### Phase 2: Authentication

**Step 1: Create API Client** (`src/api/client.ts`):

```typescript
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to all requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('alpmark_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('alpmark_token');
      localStorage.removeItem('alpmark_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

**Step 2: Create Auth API** (`src/api/auth.ts`):

```typescript
import apiClient from './client';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  user: {
    id: string;
    email: string;
    full_name: string;
    platform_role: string;
    tenant_id: string;
  };
}

export const authApi = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const { data } = await apiClient.post('/api/auth/login', credentials);
    return data;
  },
  
  getCurrentUser: async () => {
    const { data } = await apiClient.get('/api/auth/me');
    return data;
  },
  
  requestPasswordReset: async (email: string) => {
    const { data } = await apiClient.post('/api/auth/password-reset-request', { email });
    return data;
  },
};
```

**Step 3: Create Auth Context** (`src/contexts/AuthContext.tsx`):

```typescript
import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi, LoginRequest } from '../api/auth';

interface User {
  id: string;
  email: string;
  full_name: string;
  platform_role: string;
  tenant_id: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const loadUser = async () => {
      const token = localStorage.getItem('alpmark_token');
      if (token) {
        try {
          const currentUser = await authApi.getCurrentUser();
          setUser(currentUser);
        } catch (error) {
          localStorage.removeItem('alpmark_token');
          localStorage.removeItem('alpmark_user');
        }
      }
      setIsLoading(false);
    };
    loadUser();
  }, []);

  const login = async (credentials: LoginRequest) => {
    const { access_token, user: userData } = await authApi.login(credentials);
    localStorage.setItem('alpmark_token', access_token);
    localStorage.setItem('alpmark_user', JSON.stringify(userData));
    setUser(userData);
    
    // Redirect based on role
    const roleRoutes = {
      super_admin: '/admin/dashboard',
      executive_owner: '/executive/home',
      growth_manager: '/growth/home',
      retention_manager: '/retention/home',
      finance_controller: '/finance/home',
      operations_manager: '/operations/home',
      brand_admin: '/admin/home',
      support_operator: '/support/dashboard',
    };
    navigate(roleRoutes[userData.platform_role] || '/');
  };

  const logout = () => {
    localStorage.removeItem('alpmark_token');
    localStorage.removeItem('alpmark_user');
    setUser(null);
    navigate('/login');
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, logout }}>
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

**Step 4: Create Login Page** (`src/pages/auth/Login.tsx`):

```typescript
import React, { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('owner@one8.com');
  const [password, setPassword] = useState('password123');
  const [error, setError] = useState('');
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login({ email, password });
    } catch (err) {
      setError('Invalid email or password');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div>
          <h2 className="text-3xl font-bold text-center">AlpMark Intelligence</h2>
          <p className="mt-2 text-center text-gray-600">Sign in to your account</p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              required
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              required
            />
          </div>
          <button
            type="submit"
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
          >
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
};
```

---

### Phase 3: Core Components

**Step 1: KPI Card Component** (`src/components/KPICard.tsx`):

```typescript
import React, { useState } from 'react';
import { ExplainabilityModal } from './ExplainabilityModal';

interface KPICardProps {
  title: string;
  currentValue: string;
  percentageChange: number;
  trend: 'up' | 'down' | 'neutral';
  confidence: number;
  confidenceLabel: string;
  lastUpdated: string;
  explainability: {
    definition: string;
    formula: string;
    dataSources: string[];
    confidenceExplanation: string;
  };
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  currentValue,
  percentageChange,
  trend,
  confidence,
  confidenceLabel,
  lastUpdated,
  explainability,
}) => {
  const [showExplainability, setShowExplainability] = useState(false);

  const trendIcon = trend === 'up' ? '▲' : trend === 'down' ? '▼' : '—';
  const trendColor = trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-gray-600';

  return (
    <>
      <div className="bg-white rounded-lg shadow p-6 relative">
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-sm font-medium text-gray-600">{title}</h3>
          <button
            onClick={() => setShowExplainability(true)}
            className="text-gray-400 hover:text-gray-600"
          >
            ⓘ
          </button>
        </div>
        
        <div className="text-3xl font-bold mb-2">{currentValue}</div>
        
        <div className={`flex items-center text-sm ${trendColor}`}>
          <span className="mr-1">{trendIcon}</span>
          <span>{Math.abs(percentageChange)}%</span>
        </div>
        
        <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
          <span>Confidence: {confidence}% ({confidenceLabel})</span>
        </div>
        
        <div className="mt-1 text-xs text-gray-400">
          Updated: {new Date(lastUpdated).toLocaleString()}
        </div>
      </div>

      {showExplainability && (
        <ExplainabilityModal
          title={title}
          {...explainability}
          onClose={() => setShowExplainability(false)}
        />
      )}
    </>
  );
};
```

**Step 2: Explainability Modal** (`src/components/ExplainabilityModal.tsx`):

```typescript
import React from 'react';

interface ExplainabilityModalProps {
  title: string;
  definition: string;
  formula: string;
  dataSources: string[];
  confidenceExplanation: string;
  onClose: () => void;
}

export const ExplainabilityModal: React.FC<ExplainabilityModalProps> = ({
  title,
  definition,
  formula,
  dataSources,
  confidenceExplanation,
  onClose,
}) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6">
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-2xl font-bold">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl">
            ×
          </button>
        </div>

        <div className="space-y-6">
          <section>
            <h3 className="text-lg font-semibold mb-2">Definition</h3>
            <p className="text-gray-700">{definition}</p>
          </section>

          <section>
            <h3 className="text-lg font-semibold mb-2">Formula</h3>
            <pre className="bg-gray-50 p-4 rounded text-sm">{formula}</pre>
          </section>

          <section>
            <h3 className="text-lg font-semibold mb-2">Data Sources</h3>
            <ul className="space-y-1">
              {dataSources.map((source) => (
                <li key={source} className="flex items-center text-gray-700">
                  <span className="text-green-600 mr-2">✓</span>
                  {source}
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h3 className="text-lg font-semibold mb-2">Confidence</h3>
            <p className="text-gray-700">{confidenceExplanation}</p>
          </section>
        </div>

        <button
          onClick={onClose}
          className="mt-6 w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
        >
          Close
        </button>
      </div>
    </div>
  );
};
```

**Step 3: Recommendation Card** (`src/components/RecommendationCard.tsx`):

```typescript
import React from 'react';

interface RecommendationCardProps {
  id: string;
  title: string;
  summary: string;
  why: string;
  expectedImpact: Record<string, string>;
  confidence: number;
  confidenceLabel: string;
  confidenceExplanation: string;
  simulationAvailable: boolean;
  onSimulate?: () => void;
  onReview?: () => void;
  onDismiss?: () => void;
}

export const RecommendationCard: React.FC<RecommendationCardProps> = ({
  title,
  summary,
  why,
  expectedImpact,
  confidence,
  confidenceLabel,
  confidenceExplanation,
  simulationAvailable,
  onSimulate,
  onReview,
  onDismiss,
}) => {
  return (
    <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
      <h3 className="text-xl font-bold mb-2">{title}</h3>
      <p className="text-gray-600 mb-4">{summary}</p>

      <div className="bg-gray-50 p-4 rounded mb-4">
        <h4 className="font-semibold mb-2">Why?</h4>
        <div className="text-sm text-gray-700 whitespace-pre-line">{why}</div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {Object.entries(expectedImpact).map(([key, value]) => (
          <div key={key} className="bg-green-50 p-3 rounded">
            <div className="text-sm text-gray-600 capitalize">{key}</div>
            <div className="text-2xl font-bold text-green-600">{value}</div>
          </div>
        ))}
      </div>

      <div className="mb-4">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium">Confidence: {confidence}%</span>
          <span className="text-sm text-gray-600">{confidenceLabel}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-green-500 h-2 rounded-full"
            style={{ width: `${confidence}%` }}
          />
        </div>
        <p className="text-xs text-gray-500 mt-1">{confidenceExplanation}</p>
      </div>

      <div className="flex gap-2">
        {simulationAvailable && onSimulate && (
          <button
            onClick={onSimulate}
            className="flex-1 bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
          >
            Simulate
          </button>
        )}
        {onReview && (
          <button
            onClick={onReview}
            className="flex-1 bg-gray-200 text-gray-700 py-2 rounded hover:bg-gray-300"
          >
            Review
          </button>
        )}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="px-4 bg-gray-100 text-gray-600 py-2 rounded hover:bg-gray-200"
          >
            Dismiss
          </button>
        )}
      </div>
    </div>
  );
};
```

---

### Phase 4: Executive Owner Dashboard

**Step 1: Executive API** (`src/api/executive.ts`):

```typescript
import apiClient from './client';

export const executiveApi = {
  getRevenue: async () => {
    const { data } = await apiClient.get('/api/executive/revenue');
    return data;
  },
  
  getProfit: async () => {
    const { data } = await apiClient.get('/api/executive/profit');
    return data;
  },
  
  getContributionMargin: async () => {
    const { data } = await apiClient.get('/api/executive/contribution-margin');
    return data;
  },
  
  getGrowthRate: async () => {
    const { data } = await apiClient.get('/api/executive/growth-rate');
    return data;
  },
  
  getBusinessHealth: async () => {
    const { data } = await apiClient.get('/api/executive/business-health');
    return data;
  },
  
  getAlerts: async () => {
    const { data } = await apiClient.get('/api/executive/alerts');
    return data;
  },
  
  getCrossTeamSummary: async () => {
    const { data } = await apiClient.get('/api/executive/cross-team-summary');
    return data;
  },
};
```

**Step 2: Executive Home Page** (`src/pages/executive/Home.tsx`):

```typescript
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { executiveApi } from '../../api/executive';
import { recommendationApi } from '../../api/recommendations';
import { KPICard } from '../../components/KPICard';
import { RecommendationCard } from '../../components/RecommendationCard';

export const ExecutiveHome: React.FC = () => {
  const { data: revenue } = useQuery({
    queryKey: ['executive', 'revenue'],
    queryFn: executiveApi.getRevenue,
  });

  const { data: profit } = useQuery({
    queryKey: ['executive', 'profit'],
    queryFn: executiveApi.getProfit,
  });

  const { data: margin } = useQuery({
    queryKey: ['executive', 'margin'],
    queryFn: executiveApi.getContributionMargin,
  });

  const { data: growth } = useQuery({
    queryKey: ['executive', 'growth'],
    queryFn: executiveApi.getGrowthRate,
  });

  const { data: alerts } = useQuery({
    queryKey: ['executive', 'alerts'],
    queryFn: executiveApi.getAlerts,
  });

  const { data: recommendations } = useQuery({
    queryKey: ['recommendations', 'executive'],
    queryFn: () => recommendationApi.getRecommendations({ persona: 'executive_owner' }),
  });

  const { data: crossTeam } = useQuery({
    queryKey: ['executive', 'cross-team'],
    queryFn: executiveApi.getCrossTeamSummary,
  });

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Executive Dashboard</h1>

      {/* Row 1: Top KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {revenue && <KPICard {...revenue} />}
        {profit && <KPICard {...profit} />}
        {margin && <KPICard {...margin} />}
        {growth && <KPICard {...growth} />}
      </div>

      {/* Row 2: Business Health Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Business Health</h2>
        {/* Add chart component here - use recharts */}
      </div>

      {/* Row 3: Priority Alerts */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Priority Alerts</h2>
        {alerts && alerts.length > 0 ? (
          <div className="space-y-2">
            {alerts.slice(0, 5).map((alert: any) => (
              <div
                key={alert.id}
                className={`p-4 rounded border-l-4 ${
                  alert.severity === 'critical' ? 'border-red-500 bg-red-50' :
                  alert.severity === 'high' ? 'border-orange-500 bg-orange-50' :
                  'border-yellow-500 bg-yellow-50'
                }`}
              >
                <div className="font-semibold">{alert.title}</div>
                <div className="text-sm text-gray-600">{alert.description}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No active alerts</p>
        )}
      </div>

      {/* Row 4: Strategic Recommendations */}
      <div>
        <h2 className="text-xl font-bold mb-4">Strategic Recommendations</h2>
        {recommendations && recommendations.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {recommendations.slice(0, 4).map((rec: any) => (
              <RecommendationCard key={rec.id} {...rec} />
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No recommendations available</p>
        )}
      </div>

      {/* Row 5: Cross-Team Rollup */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {crossTeam && Object.entries(crossTeam).map(([dept, status]: any) => (
          <div key={dept} className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-2 capitalize">{dept}</h3>
            <div className={`text-2xl font-bold ${
              status === 'healthy' ? 'text-green-600' :
              status === 'risk' ? 'text-yellow-600' :
              'text-red-600'
            }`}>
              {status.toUpperCase()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

### Phase 5: Growth Manager Dashboard

**Step 1: Growth API** (`src/api/growth.ts`):

```typescript
import apiClient from './client';

export const growthApi = {
  getMarketingSpend: async () => {
    const { data } = await apiClient.get('/api/growth/marketing-spend');
    return data;
  },
  
  getRoas: async () => {
    const { data } = await apiClient.get('/api/growth/roas');
    return data;
  },
  
  getCac: async () => {
    const { data } = await apiClient.get('/api/growth/cac');
    return data;
  },
  
  getPaybackPeriod: async () => {
    const { data } = await apiClient.get('/api/growth/payback-period');
    return data;
  },
  
  getChannelPerformance: async () => {
    const { data } = await apiClient.get('/api/growth/channel-performance');
    return data;
  },
  
  getCampaigns: async () => {
    const { data } = await apiClient.get('/api/growth/campaigns');
    return data;
  },
  
  getSpendByChannel: async () => {
    const { data } = await apiClient.get('/api/growth/spend-by-channel');
    return data;
  },
  
  getRoasTrend: async () => {
    const { data } = await apiClient.get('/api/growth/roas-trend');
    return data;
  },
};
```

**Step 2: Growth Home Page** (`src/pages/growth/Home.tsx`):

```typescript
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { growthApi } from '../../api/growth';
import { KPICard } from '../../components/KPICard';

export const GrowthHome: React.FC = () => {
  const { data: spend } = useQuery({
    queryKey: ['growth', 'spend'],
    queryFn: growthApi.getMarketingSpend,
  });

  const { data: roas } = useQuery({
    queryKey: ['growth', 'roas'],
    queryFn: growthApi.getRoas,
  });

  const { data: cac } = useQuery({
    queryKey: ['growth', 'cac'],
    queryFn: growthApi.getCac,
  });

  const { data: payback } = useQuery({
    queryKey: ['growth', 'payback'],
    queryFn: growthApi.getPaybackPeriod,
  });

  const { data: campaigns } = useQuery({
    queryKey: ['growth', 'campaigns'],
    queryFn: growthApi.getCampaigns,
  });

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Growth & Performance</h1>

      {/* Row 1: Top KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {spend && <KPICard {...spend} />}
        {roas && <KPICard {...roas} />}
        {cac && <KPICard {...cac} />}
        {payback && <KPICard {...payback} />}
      </div>

      {/* Row 2: Channel Performance Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Channel Performance</h2>
        {/* Add bubble chart here */}
      </div>

      {/* Row 3: Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-bold mb-4">Spend by Channel</h3>
          {/* Add stacked bar chart */}
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-bold mb-4">ROAS Trend</h3>
          {/* Add line chart */}
        </div>
      </div>

      {/* Row 4: Campaign Performance Table */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Campaign Performance</h2>
        {campaigns && campaigns.length > 0 ? (
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="text-left p-2">Campaign</th>
                <th className="text-right p-2">Spend</th>
                <th className="text-right p-2">Revenue</th>
                <th className="text-right p-2">ROAS</th>
                <th className="text-right p-2">CAC</th>
                <th className="text-right p-2">Margin</th>
                <th className="text-right p-2">Trend</th>
              </tr>
            </thead>
            <tbody>
              {campaigns.map((campaign: any) => (
                <tr key={campaign.id} className="border-b hover:bg-gray-50">
                  <td className="p-2">{campaign.name}</td>
                  <td className="text-right p-2">{campaign.spend}</td>
                  <td className="text-right p-2">{campaign.revenue}</td>
                  <td className="text-right p-2">{campaign.roas}</td>
                  <td className="text-right p-2">{campaign.cac}</td>
                  <td className="text-right p-2">{campaign.margin}</td>
                  <td className="text-right p-2">{campaign.trend}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-gray-500">No campaign data available</p>
        )}
      </div>
    </div>
  );
};
```

---

### Phase 6: Routing & Navigation

**Step 1: Create Protected Route** (`src/components/ProtectedRoute.tsx`):

```typescript
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowedRoles,
}) => {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user!.platform_role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
};
```

**Step 2: Create Sidebar** (`src/components/Sidebar.tsx`):

```typescript
import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useFeatures } from '../contexts/FeaturesContext';

export const Sidebar: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const features = useFeatures();

  const getNavItems = () => {
    switch (user?.platform_role) {
      case 'executive_owner':
        return [
          { path: '/executive/home', label: 'Home' },
          { path: '/executive/analytics', label: 'Analytics' },
          { path: '/recommendations', label: 'Recommendations', feature: 'recommendations' },
          { path: '/simulations', label: 'Simulations', feature: 'simulations' },
          { path: '/saved-views', label: 'Saved Views', feature: 'saved_views' },
          { path: '/reports', label: 'Reports' },
        ];
      
      case 'growth_manager':
        return [
          { path: '/growth/home', label: 'Home' },
          { path: '/growth/analytics', label: 'Analytics' },
          { path: '/recommendations', label: 'Recommendations', feature: 'recommendations' },
          { path: '/simulations', label: 'Simulations', feature: 'simulations' },
          { path: '/saved-views', label: 'Saved Views', feature: 'saved_views' },
          { path: '/exports', label: 'Exports', feature: 'exports' },
        ];
      
      case 'brand_admin':
        return [
          { path: '/admin/home', label: 'Home' },
          { path: '/admin/users', label: 'Users' },
          { path: '/admin/roles', label: 'Roles' },
          { path: '/admin/integrations', label: 'Integrations' },
          { path: '/admin/billing', label: 'Billing' },
          { path: '/admin/audit-logs', label: 'Audit Logs' },
        ];
      
      // Add more roles...
      default:
        return [];
    }
  };

  const navItems = getNavItems().filter(item => 
    !item.feature || features[item.feature]
  );

  return (
    <div className="w-64 bg-gray-900 text-white h-screen flex flex-col">
      <div className="p-4">
        <h1 className="text-2xl font-bold">AlpMark</h1>
        <p className="text-sm text-gray-400">{user?.full_name}</p>
      </div>

      <nav className="flex-1 overflow-y-auto">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`block px-4 py-3 hover:bg-gray-800 ${
              location.pathname === item.path ? 'bg-gray-800 border-l-4 border-blue-500' : ''
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="p-4 border-t border-gray-800">
        <button
          onClick={logout}
          className="w-full text-left px-4 py-2 hover:bg-gray-800 rounded"
        >
          Logout
        </button>
      </div>
    </div>
  );
};
```

**Step 3: Main App Router** (`src/App.tsx`):

```typescript
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { FeaturesProvider } from './contexts/FeaturesContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Sidebar } from './components/Sidebar';
import { Login } from './pages/auth/Login';
import { ExecutiveHome } from './pages/executive/Home';
import { GrowthHome } from './pages/growth/Home';
import { RetentionHome } from './pages/retention/Home';
import { FinanceHome } from './pages/finance/Home';
import { OperationsHome } from './pages/operations/Home';
import { AdminHome } from './pages/admin/Home';

const queryClient = new QueryClient();

const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-gray-50">
        {children}
      </main>
    </div>
  );
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <FeaturesProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              
              <Route path="/executive/*" element={
                <ProtectedRoute allowedRoles={['executive_owner']}>
                  <AppLayout>
                    <Routes>
                      <Route path="home" element={<ExecutiveHome />} />
                    </Routes>
                  </AppLayout>
                </ProtectedRoute>
              } />

              <Route path="/growth/*" element={
                <ProtectedRoute allowedRoles={['growth_manager']}>
                  <AppLayout>
                    <Routes>
                      <Route path="home" element={<GrowthHome />} />
                    </Routes>
                  </AppLayout>
                </ProtectedRoute>
              } />

              <Route path="/retention/*" element={
                <ProtectedRoute allowedRoles={['retention_manager']}>
                  <AppLayout>
                    <Routes>
                      <Route path="home" element={<RetentionHome />} />
                    </Routes>
                  </AppLayout>
                </ProtectedRoute>
              } />

              <Route path="/finance/*" element={
                <ProtectedRoute allowedRoles={['finance_controller']}>
                  <AppLayout>
                    <Routes>
                      <Route path="home" element={<FinanceHome />} />
                    </Routes>
                  </AppLayout>
                </ProtectedRoute>
              } />

              <Route path="/operations/*" element={
                <ProtectedRoute allowedRoles={['operations_manager']}>
                  <AppLayout>
                    <Routes>
                      <Route path="home" element={<OperationsHome />} />
                    </Routes>
                  </AppLayout>
                </ProtectedRoute>
              } />

              <Route path="/admin/*" element={
                <ProtectedRoute allowedRoles={['brand_admin']}>
                  <AppLayout>
                    <Routes>
                      <Route path="home" element={<AdminHome />} />
                    </Routes>
                  </AppLayout>
                </ProtectedRoute>
              } />

              <Route path="/" element={<Navigate to="/login" replace />} />
            </Routes>
          </FeaturesProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
```

---

### Phase 7: Deployment to Replit

**Step 1: Create `.replit` file**:

```toml
run = "npm run dev"

[nix]
channel = "stable-22_11"

[deployment]
run = ["npm", "run", "build"]
deploymentTarget = "static"

[[ports]]
localPort = 5173
externalPort = 80
```

**Step 2: Create `replit.nix` file**:

```nix
{ pkgs }: {
  deps = [
    pkgs.nodejs-18_x
  ];
}
```

**Step 3: Update `package.json`**:

```json
{
  "scripts": {
    "dev": "vite --host 0.0.0.0 --port 5173",
    "build": "tsc && vite build",
    "preview": "vite preview --host 0.0.0.0"
  }
}
```

**Step 4: Deploy**:

1. Create new Replit project
2. Import from GitHub or upload files
3. Add `.env` file with `VITE_API_BASE_URL`
4. Click "Run"
5. Replit will install dependencies and start dev server
6. For production: click "Deploy" → Static site

---

## Summary

This guide provides:

1. ✅ **Complete Architecture** - Multi-tenant, invitation-only, persona-based
2. ✅ **All 178 API Endpoints** - Organized by domain with request/response examples
3. ✅ **8 Persona Specifications** - Exact dashboard layouts with API mappings
4. ✅ **Authentication Flow** - JWT, login, token management, protected routes
5. ✅ **Supporting Systems** - Recommendations, simulations, explainability, confidence
6. ✅ **Feature Flags** - Subscription-based feature control
7. ✅ **Step-by-Step Instructions** - From project init to deployment

**Next Steps**:

1. Initialize React project with Vite
2. Implement authentication (Phase 2)
3. Build core components (Phase 3)
4. Build Executive Owner dashboard (Phase 4)
5. Build remaining persona dashboards (Phase 5)
6. Add routing & navigation (Phase 6)
7. Deploy to Replit (Phase 7)

**Demo Credentials**:
- Executive Owner: `owner@one8.com` / `password123`
- Growth Manager: `growth@one8.com` / `password123`
- Brand Admin: `admin@one8.com` / `password123`

**Backend URL**: `https://alpmark-production.up.railway.app`

This document contains everything needed to build a production-ready frontend for AlpMark Intelligence Platform.

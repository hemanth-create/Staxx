# Staxx Intelligence — Frontend Dashboard

**Premium glassmorphic SaaS dashboard for LLM cost optimization.**

## 🎨 Design System

### Aesthetic
- **Dark Mode**: `#09090b` background (zinc-950)
- **Glassmorphism**: 20px blur with semi-transparent surfaces
- **Color Palette**:
  - Primary accent: `#0ea5e9` (sky-500)
  - Success: `#22c55e` (green-500)
  - Warning: `#f59e0b` (amber-500)
  - Danger: `#ef4444` (red-500)
- **Typography**: Inter (body), JetBrains Mono (metrics)
- **Motion**: Framer Motion for page transitions, staggered reveals, number animations

### Key Components
- **GlassPanel**: Reusable glassmorphic container
- **MetricCard**: Animated number counters with sparkline charts
- **SparkLine**: Tiny inline charts for trend visualization
- **Sidebar**: Navigation with active state indicators
- **TopBar**: Breadcrumb, time range selector, notifications, user menu
- **DashboardLayout**: Main layout wrapper (sidebar + topbar + content)

## 📁 File Structure

```
src/
├── App.jsx                          # Router setup
├── main.jsx                         # Vite entry point
├── index.css                        # Tailwind + custom utilities
├── components/
│   ├── GlassPanel.jsx               # Glassmorphic container
│   ├── MetricCard.jsx               # Metric display with animations
│   ├── SparkLine.jsx                # Inline sparkline chart
│   ├── Sidebar.jsx                  # Left navigation
│   ├── TopBar.jsx                   # Header with search, notifications
│   ├── TimeRangeSelector.jsx        # Time range pill buttons
│   └── LoadingSkeleton.jsx          # Loading placeholders
├── layouts/
│   └── DashboardLayout.jsx          # Main layout wrapper
├── pages/
│   └── DashboardHome.jsx            # Dashboard overview (default view)
├── hooks/
│   └── useCountUp.js                # Animated number counter hook
├── theme/
│   └── chartTheme.js                # Recharts dark theme config
└── utils/
    └── mockData.js                  # Mock data for development
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

The dashboard runs on `http://localhost:3000` with HMR enabled.

### Build for Production

```bash
npm run build
npm run preview
```

## 🎯 Features

### Dashboard Home Page
1. **Top Row**: 4 key metrics with animations
   - Total Spend (MTD)
   - Potential Savings
   - Active Models
   - API Calls (MTD)

2. **Spend Over Time**: Area chart with actual vs. projected spend
   - Gradient fill, animated on mount
   - Glowing hover tooltips

3. **Bottom Row** (Two panels):
   - **Left**: "Spend by Task Type" — horizontal bar chart
   - **Right**: "Active Swap Recommendations" — list of actionable swaps with confidence badges

### Key Interactions
- Number counting animations on page load
- Staggered component reveals using Framer Motion
- Trend indicators (green/red arrows based on metric type)
- Time range selector (24h, 7d, 30d, 90d, Custom)
- User dropdown menu with profile, billing, signout
- Responsive design: sidebar collapses on mobile

## 🔌 API Integration

### Mock Data
Currently, the dashboard uses mock data from `src/utils/mockData.js`. To connect to the platform backend:

1. Update `src/utils/mockData.js` to fetch from `/api/v1/billing/usage`, `/api/v1/platform/*` endpoints
2. Use axios (already in dependencies) for API calls
3. Example:

```javascript
// In DashboardHome.jsx or a custom hook
useEffect(() => {
  const fetchMetrics = async () => {
    try {
      const { data } = await axios.get("/api/v1/billing/usage");
      setMetrics(data);
    } catch (err) {
      console.error("Failed to fetch metrics", err);
    }
  };
  fetchMetrics();
}, []);
```

## 🎨 Styling

### Tailwind CSS
- Using `@tailwindcss/vite` for zero-build CSS
- Dark mode enabled by default
- Custom colors defined in `tailwind.config.js`

### Custom CSS Classes
- `.glass-panel`: Semi-transparent panel with blur
- `.glass-card`: More prominent gradient glassmorphic card
- Custom scrollbar styling for premium feel

### Responsive Breakpoints
- Mobile first approach
- `md:` (768px) and `lg:` (1024px) breakpoints used throughout
- Sidebar collapses to mobile overlay on small screens

## 🔮 Future Pages (Skeleton)

The Router is set up to support these future pages (commented in `App.jsx`):
- `/cost-topology` — Cost Topology visualization
- `/shadow-evals` — Shadow Evaluation results
- `/recommendations` — Swap Recommendations detail page
- `/roi` — ROI Projections
- `/alerts` — Alert management
- `/settings` — Organization & billing settings

## 📊 Charts

### Recharts Setup
- Custom dark theme defined in `src/theme/chartTheme.js`
- Gradient fills for visual depth
- Animated on mount (1000-1200ms duration)
- Glowing tooltips on hover
- Responsive container sizing

### Supported Charts
- AreaChart (Spend Over Time)
- BarChart (Task Type breakdown)
- Pie/Donut (future: model allocation)
- Sparkline (inline trend charts)

## 🎬 Animation Strategy

### Framer Motion
- **Page transitions**: Fade + slide (300ms)
- **Component reveals**: Staggered children with 100ms delay
- **Number counting**: 1 second duration with smooth easing
- **Hover effects**: Subtle scale and color transitions

## 📦 Dependencies

- **React 19**: UI framework
- **React Router 6**: Client-side routing
- **Framer Motion**: Animations
- **Recharts**: Data visualization
- **Lucide React**: Icon library
- **Tailwind CSS 4**: Styling
- **Axios**: HTTP client
- **@tailwindcss/vite**: Zero-config Tailwind

## 🔐 Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Available variables:
- `VITE_API_BASE_URL` — Backend API endpoint (default: `http://localhost:8000/api/v1`)

## ⚡ Performance Optimizations

- Lazy component loading via React Router
- Motion value transforms for optimized number animations
- Recharts ResponsiveContainer for efficient chart rendering
- Custom scrollbar for lightweight styling
- Backdrop-filter blur for GPU-accelerated glassmorphism

## 🐛 Debugging

### Common Issues

1. **Charts not rendering**
   - Ensure Recharts ResponsiveContainer has a parent with defined height
   - Check console for data prop errors

2. **Animations stuttering**
   - Verify GPU acceleration is enabled in browser dev tools
   - Reduce number of simultaneous animations if needed

3. **API calls failing**
   - Check proxy config in `vite.config.js`
   - Ensure backend is running on port 8000

## 📝 Notes

- The dashboard is fully responsive and mobile-friendly
- All numbers are formatted with thousands separators and currency symbols
- Trend indicators automatically color based on metric context (savings = green up, costs = red up)
- Loading skeletons match the glassmorphic design system
- All icons use Lucide React for consistency

---

**Built with ❤️ for premium SaaS.**

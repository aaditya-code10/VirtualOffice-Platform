import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  ClipboardList,
  Database,
  BarChart3,
  FileText,
  CheckSquare,
  Settings,
  Sparkles,
  LogOut,
  Building,
} from "lucide-react";
import { BrandLogo } from "../brand/BrandLogo";
import { useAuth } from "../../auth";

interface GlassSidebarProps {
  onNewAssessment?: () => void;
}

export function GlassSidebar({ onNewAssessment }: GlassSidebarProps) {
  const { user, company, logout } = useAuth();

  const navItems = [
    { to: "/", label: "Home", icon: LayoutDashboard, end: true },
    { to: "/office", label: "Virtual Office", icon: Users },
    { to: "/work-orders", label: "Work Orders", icon: ClipboardList },
    { to: "/knowledge", label: "Knowledge", icon: Database },
    { to: "/analytics", label: "Analytics", icon: BarChart3 },
    { to: "/reports", label: "Executive Reports", icon: FileText },
    { to: "/approvals", label: "Approvals", icon: CheckSquare },
    { to: "/company", label: "Company Twin", icon: Building },
    { to: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <aside className="glass-sidebar">
      {/* Brand Header */}
      <div className="glass-sidebar-brand">
        <BrandLogo size="md" />
      </div>

      {/* Primary Action Button */}
      {onNewAssessment && (
        <div className="glass-sidebar-action">
          <button
            type="button"
            className="sidebar-new-btn"
            onClick={onNewAssessment}
          >
            <Sparkles size={14} className="sidebar-action-icon" />
            <span>New Assessment</span>
          </button>
        </div>
      )}

      {/* Navigation Links */}
      <nav className="glass-sidebar-nav">
        <div className="nav-group-label">OPERATING SYSTEM</div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `glass-nav-item ${isActive ? "glass-nav-item--active" : ""}`
              }
            >
              <div className="nav-icon-wrapper">
                <Icon size={16} />
              </div>
              <span className="nav-label">{item.label}</span>
              <span className="nav-active-pill" aria-hidden="true" />
            </NavLink>
          );
        })}
      </nav>

      {/* User profile / session footer */}
      <div className="glass-sidebar-footer">
        <div className="user-profile-glass">
          <div className="user-avatar-glass">
            <span>{user?.full_name?.charAt(0) || "U"}</span>
          </div>
          <div className="user-info-text">
            <span className="user-name">{user?.full_name || "Enterprise User"}</span>
            <span className="user-workspace">
              {company?.name || user?.role || "Digital Workspace"}
            </span>
          </div>
          <button
            type="button"
            className="user-logout-btn"
            onClick={logout}
            title="Sign out of workspace"
            aria-label="Sign out"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  );
}

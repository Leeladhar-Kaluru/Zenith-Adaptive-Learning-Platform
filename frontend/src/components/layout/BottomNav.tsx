import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, Compass, Target, MessageSquare, Award } from 'lucide-react';
import styles from './BottomNav.module.css';

export const BottomNav: React.FC = () => {
  const navItems = [
    { to: '/', label: 'Home', icon: <Home size={18} /> },
    { to: '/explore', label: 'Explore', icon: <Compass size={18} /> },
    { to: '/practice', label: 'Practice', icon: <Target size={18} /> },
    { to: '/ask', label: 'Tutor', icon: <MessageSquare size={18} /> },
    { to: '/achievements', label: 'Badges', icon: <Award size={18} /> }
  ];

  return (
    <nav className={styles.bottomNav} aria-label="Mobile Navigation">
      <ul className={styles.navList}>
        {navItems.map((item) => (
          <li key={item.to} className={styles.navItem}>
            <NavLink
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `${styles.navLink} ${isActive ? styles.navLinkActive : ''}`
              }
            >
              {item.icon}
              <span>{item.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
};

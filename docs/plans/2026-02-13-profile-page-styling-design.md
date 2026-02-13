# Profile Page Styling Design

**Date:** 2026-02-13
**Status:** Approved
**Type:** Frontend Styling

## Overview

Design and implement CSS styling for the user profile page, creating a clean, centered card layout with an initials-based avatar that follows the existing Material Design 3 aesthetic.

## Requirements

- Display user profile information in a clean, professional layout
- Include an avatar using user initials (no file uploads required)
- Reuse existing CSS components and design patterns
- Maintain responsive design for mobile devices
- Follow Material Design 3 principles established in the codebase

## Design Decisions

### Layout Approach: Centered Card with Top Avatar

**Selected:** Approach 1 - Centered Card with Top Avatar
**Reasoning:**
- Leverages existing CSS components (`.container`, `.data-list`)
- Clean, focused design appropriate for internal dashboard
- Minimal new CSS required
- Mobile-friendly and easily extendable
- Professional appearance with clear visual hierarchy

**Rejected Alternatives:**
- Split Layout (Header Banner + Info Card) - Too complex, redundant header
- Horizontal Avatar + Info Layout - Less prominent avatar, harder to scan

### Information Display

**Content:**
- User Info Card with basic details only (focused approach)
- Avatar with user initials
- Username, email, full name, registration date
- Data displayed using existing `.data-list` table component

**Avatar Design:**
- Circular initials badge (100px diameter, 80px on mobile)
- Gradient background (blue → green) matching brand colors
- White text, uppercase initials
- Material Design 3 elevation shadow

## HTML Structure

```html
<div class="profile-page-wrapper">
    <div class="profile-card container">
        <!-- Avatar Section -->
        <div class="profile-header">
            <div class="profile-avatar">
                <span class="avatar-initials">JD</span>
            </div>
            <h1 class="profile-username">{{ user.username }}</h1>
            <p class="profile-subtitle">{{ user.email }}</p>
        </div>

        <!-- User Info Section -->
        <table class="data-list">
            <tr>
                <th>Nome Utente</th>
                <td>{{ user.username }}</td>
            </tr>
            <tr>
                <th>Email</th>
                <td>{{ user.email }}</td>
            </tr>
            <tr>
                <th>Nome Completo</th>
                <td>{{ user.first_name }} {{ user.last_name }}</td>
            </tr>
            <tr>
                <th>Data Registrazione</th>
                <td>{{ user.date_joined|date:"d/m/Y" }}</td>
            </tr>
        </table>
    </div>
</div>
```

## CSS Specifications

### Desktop Styles

**Profile Page Wrapper:**
- Flexbox centering
- 20px padding

**Profile Card:**
- Max-width: 600px
- Full width on smaller screens
- Centered text alignment
- Reuses `.container` base styles

**Profile Header:**
- Flexbox column layout
- 32px bottom margin
- 24px bottom padding
- Border separator (1px solid `--border-clr`)

**Profile Avatar:**
- 100px × 100px circle
- Gradient: `linear-gradient(135deg, var(--primary-clr), var(--serravalle-light-green-clr))`
- Box shadow: `0px 4px 12px rgba(0, 89, 150, 0.2)`
- 16px bottom margin

**Avatar Initials:**
- 36px font size
- 600 font weight
- White color
- Uppercase transform
- Radio Canada font family

**Profile Username:**
- 28px font size
- 600 font weight
- 8px top margin, 4px bottom margin

**Profile Subtitle:**
- 16px font size
- Secondary text color
- No margin

### Mobile Styles (@media max-width: 800px)

**Adjustments:**
- Profile page wrapper: 10px padding
- Profile card: 20px padding
- Avatar: 80px × 80px
- Avatar initials: 28px font size
- Username: 24px font size
- Subtitle: 14px font size

**Inherited Responsive:**
- Data list table uses existing responsive styles (horizontal scroll if needed)

## Integration Plan

### Files to Modify

1. **`templates/profiles/profile.html`**
   - Replace current basic list with new profile card layout
   - Add initials generation: `{{ user.username|slice:":2"|upper }}`

2. **`static/css/style.css`**
   - Add profile CSS section (before or after PDF overlay section)
   - Add responsive profile styles to existing `@media(max-width: 800px)` block

3. **`apps/profiles/views.py`** (Optional enhancement)
   - Add method to generate proper initials from first/last name
   - Fallback to username if names not set

### Initials Generation

**Simple approach (template filter):**
```django
{{ user.username|slice:":2"|upper }}
```

**Better approach (view logic):**
```python
def get_user_initials(user):
    if user.first_name and user.last_name:
        return f"{user.first_name[0]}{user.last_name[0]}".upper()
    return user.username[:2].upper()
```

## Design Consistency

**Alignment with Existing Design System:**
- Uses established CSS variables (colors, fonts)
- Follows Material Design 3 elevation patterns
- Reuses `.container` and `.data-list` components
- Matches gradient patterns from home page
- Consistent border radius (50% for avatar, default for card)
- Follows established responsive breakpoint (800px)

## Future Extensibility

**Easy Extensions:**
- Add more data rows to the `.data-list` table
- Add action buttons below the info table (Edit Profile, Change Password)
- Wrap multiple cards in `.grid-container.columns-2` for multi-card layout
- Add stats card, recent activity card, or settings card

**No Breaking Changes:**
- Design is additive, doesn't modify existing components
- Can evolve to dashboard-style with multiple cards without refactoring

## Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- CSS Grid and Flexbox support required (standard in all modern browsers)
- Gradient backgrounds widely supported
- No JavaScript required for core functionality

## Accessibility Considerations

- Semantic HTML structure
- Proper heading hierarchy (h1 for username)
- Table markup for data list (screen reader friendly)
- Sufficient color contrast for text
- Responsive text sizing

## Success Criteria

- Profile page displays user information in a clean, centered card
- Avatar shows user initials with brand gradient
- Page is fully responsive on mobile devices
- Design matches Material Design 3 aesthetic
- Reuses existing CSS components
- No JavaScript required
- Page loads quickly with minimal new CSS

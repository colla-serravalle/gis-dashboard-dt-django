# Profile Page Styling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement styled profile page with centered card layout and initials avatar following Material Design 3 principles.

**Architecture:** Frontend-only changes updating HTML template and CSS. Reuses existing `.container` and `.data-list` components with new profile-specific styles for avatar and layout.

**Tech Stack:** Django templates, CSS3, existing Material Design 3 design system

---

## Task 1: Update Profile Template HTML

**Files:**
- Modify: `templates/profiles/profile.html` (complete rewrite)

**Step 1: Read current template**

Run: `cat templates/profiles/profile.html`
Expected: See basic list structure with username and email

**Step 2: Update template with new profile card structure**

Replace entire content of `templates/profiles/profile.html`:

```django
{% extends 'base.html' %}
{% load static %}

{% block title %}Profilo Utente - GIS Dashboard{% endblock %}

{% block content %}
<div class="profile-page-wrapper">
    <div class="profile-card container">
        <!-- Avatar Section -->
        <div class="profile-header">
            <div class="profile-avatar">
                <span class="avatar-initials">{{ user.username|slice:":2"|upper }}</span>
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
                <td>{% if user.first_name or user.last_name %}{{ user.first_name }} {{ user.last_name }}{% else %}-{% endif %}</td>
            </tr>
            <tr>
                <th>Data Registrazione</th>
                <td>{{ user.date_joined|date:"d/m/Y" }}</td>
            </tr>
        </table>
    </div>
</div>
{% endblock %}
```

**Step 3: Verify template syntax**

Run: `python manage.py check`
Expected: System check identified no issues (0 silenced).

**Step 4: Commit template changes**

```bash
git add templates/profiles/profile.html
git commit -m "feat(profile): update template with card layout and avatar

- Add profile-page-wrapper and profile-card structure
- Add profile-header with avatar using initials
- Replace basic list with data-list table
- Add fallback for missing first/last name

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Add Desktop CSS Styles

**Files:**
- Modify: `static/css/style.css` (add new section after line 1519)

**Step 1: Locate insertion point in CSS file**

Run: `tail -20 static/css/style.css`
Expected: See the PDF overlay styles ending around line 1519

**Step 2: Add profile page CSS section**

Append to `static/css/style.css` (after line 1519, before or after PDF overlay section):

```css

/* ========================================
   PROFILE PAGE STYLES - Material Design 3
   ======================================== */

/* Centers the profile card on the page */
.profile-page-wrapper {
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 20px;
}

/* Profile card container */
.profile-card {
    max-width: 600px;
    width: 100%;
    text-align: center;
}

/* Profile header section (avatar + name + email) */
.profile-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 32px;
    padding-bottom: 24px;
    border-bottom: 1px solid var(--border-clr);
}

/* Circular avatar with initials */
.profile-avatar {
    width: 100px;
    height: 100px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--primary-clr), var(--serravalle-light-green-clr));
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
    box-shadow: 0px 4px 12px rgba(0, 89, 150, 0.2);
}

.avatar-initials {
    color: var(--base-clr);
    font-size: 36px;
    font-weight: 600;
    font-family: var(--font-tester);
    text-transform: uppercase;
}

/* Username styling */
.profile-username {
    font-size: 28px;
    font-weight: 600;
    color: var(--text-clr);
    margin: 8px 0 4px 0;
    font-family: var(--font-tester);
}

/* Email subtitle */
.profile-subtitle {
    font-size: 16px;
    color: var(--secondary-text-clr);
    margin: 0;
}

/* Info table alignment */
.profile-card .data-list {
    text-align: left;
}
```

**Step 3: Verify CSS syntax**

Run: `python manage.py collectstatic --dry-run --noinput`
Expected: No syntax errors, shows static files that would be collected

**Step 4: Commit desktop CSS**

```bash
git add static/css/style.css
git commit -m "feat(profile): add desktop CSS styles for profile page

- Add profile-page-wrapper for centering
- Add profile-header with flexbox layout
- Add profile-avatar with gradient background (blue to green)
- Add avatar-initials styling (36px, white, uppercase)
- Add profile-username and profile-subtitle styles
- Align data-list table to left within card

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Add Responsive Mobile CSS Styles

**Files:**
- Modify: `static/css/style.css` (inside existing @media block at line 851)

**Step 1: Locate mobile media query**

Run: `grep -n "@media(max-width: 800px)" static/css/style.css`
Expected: Line 851 shows the start of mobile media query

**Step 2: Add responsive profile styles**

Add inside the existing `@media(max-width: 800px)` block (before the closing brace at line 1011):

```css

    /* PROFILE PAGE RESPONSIVE */
    .profile-page-wrapper {
        padding: 10px;
    }

    .profile-card {
        max-width: 100%;
        padding: 20px;
    }

    /* Slightly smaller avatar on mobile */
    .profile-avatar {
        width: 80px;
        height: 80px;
    }

    .avatar-initials {
        font-size: 28px;
    }

    /* Smaller heading on mobile */
    .profile-username {
        font-size: 24px;
    }

    .profile-subtitle {
        font-size: 14px;
    }
```

**Step 3: Verify responsive CSS syntax**

Run: `python manage.py collectstatic --dry-run --noinput`
Expected: No syntax errors

**Step 4: Commit responsive CSS**

```bash
git add static/css/style.css
git commit -m "feat(profile): add responsive mobile styles

- Reduce padding on mobile (10px)
- Scale down avatar from 100px to 80px
- Reduce font sizes for username and subtitle
- Adjust profile-card padding for mobile

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Manual Visual Testing

**Files:**
- None (testing only)

**Step 1: Start development server**

Run: `python manage.py runserver`
Expected: Server starts on http://127.0.0.1:8000/

**Step 2: Navigate to profile page**

Action: Open browser and go to `http://127.0.0.1:8000/profiles/`
Expected: See login page (if not logged in)

**Step 3: Login and view profile**

Action:
1. Login with valid credentials
2. Click "Profilo" link in sidebar
3. View profile page

Expected Visual Checklist:
- ✓ Profile card is centered on page
- ✓ Avatar circle displays with blue→green gradient
- ✓ Initials appear in white, uppercase (first 2 letters of username)
- ✓ Username displays below avatar (28px, bold)
- ✓ Email displays below username in gray
- ✓ Horizontal line separates header from info
- ✓ Data table shows: Nome Utente, Email, Nome Completo, Data Registrazione
- ✓ Table uses existing data-list styling (rounded corners, hover effect)
- ✓ Card has max-width of 600px on desktop
- ✓ Design matches Material Design 3 aesthetic

**Step 4: Test mobile responsive**

Action:
1. Open browser DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Select iPhone or Android device
4. Refresh profile page

Expected Mobile Checklist:
- ✓ Avatar scales down to 80px
- ✓ Username font size reduces to 24px
- ✓ Email font size reduces to 14px
- ✓ Card uses full width with appropriate padding
- ✓ Table remains readable (scrollable if needed)
- ✓ Layout doesn't break or overflow

**Step 5: Test with different usernames**

Action: Test initials generation with:
- Short username (2 chars): Should show 2 chars
- Long username: Should show first 2 chars
- User with first/last name: Should still use username for initials

Expected: Initials always display correctly (2 uppercase letters)

**Step 6: Stop development server**

Run: `Ctrl+C` in terminal
Expected: Server stops cleanly

---

## Task 5: Optional Enhancement - Better Initials Logic

**Files:**
- Modify: `apps/profiles/views.py`

**Note:** This task is OPTIONAL. The template already works with username initials. Only implement if you want proper first name + last name initials.

**Step 1: Read current view**

Run: `cat apps/profiles/views.py`
Expected: See basic ProfileView with get() method

**Step 2: Enhance view with initials method**

Update `apps/profiles/views.py`:

```python
"""Core application views."""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.decorators import method_decorator


@method_decorator(login_required, name='dispatch')
class ProfileView(View):
    """Profile page view - displays user information."""

    template_name = 'profiles/profile.html'

    def get(self, request):
        context = {
            'initials': self.get_user_initials(request.user)
        }
        return render(request, self.template_name, context)

    def get_user_initials(self, user):
        """Generate user initials from first/last name or username."""
        if user.first_name and user.last_name:
            return f"{user.first_name[0]}{user.last_name[0]}".upper()
        return user.username[:2].upper()
```

**Step 3: Update template to use context initials**

Modify `templates/profiles/profile.html` line 11:

Change from:
```django
<span class="avatar-initials">{{ user.username|slice:":2"|upper }}</span>
```

To:
```django
<span class="avatar-initials">{{ initials }}</span>
```

**Step 4: Test initials generation**

Run: `python manage.py shell`

```python
from apps.profiles.views import ProfileView
from django.contrib.auth import get_user_model
User = get_user_model()

# Test with user that has first/last name
user = User.objects.first()
view = ProfileView()
print(view.get_user_initials(user))
```

Expected: Returns 2 uppercase letters

**Step 5: Commit enhancement (if implemented)**

```bash
git add apps/profiles/views.py templates/profiles/profile.html
git commit -m "feat(profile): enhance initials generation logic

- Add get_user_initials method to ProfileView
- Prefer first_name + last_name initials over username
- Fallback to username if names not set
- Pass initials to template via context

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Final Verification and Documentation

**Files:**
- None (verification only)

**Step 1: Run Django checks**

Run: `python manage.py check --deploy`
Expected: No critical issues

**Step 2: Verify all commits**

Run: `git log --oneline -5`
Expected: See 3-4 commits for this feature

**Step 3: Visual regression check**

Action:
1. Start dev server: `python manage.py runserver`
2. Visit profile page: `http://127.0.0.1:8000/profiles/`
3. Compare against design document specifications

Expected: Profile page matches approved design:
- ✓ Centered card layout (max 600px)
- ✓ Initials avatar with gradient
- ✓ Username and email displayed
- ✓ Data table with user info
- ✓ Responsive on mobile
- ✓ Material Design 3 aesthetic

**Step 4: Check for CSS conflicts**

Action:
1. Visit other pages: home, reports list, report detail
2. Verify new CSS doesn't affect other pages

Expected: Other pages look unchanged

**Step 5: Browser compatibility check**

Action: Test in available browsers (Chrome, Firefox, Edge, Safari)
Expected: Consistent appearance across browsers

**Step 6: Document completion**

Update design doc status if needed:
- Mark implementation as COMPLETE
- Note any deviations from original design
- Document any issues encountered

---

## Success Criteria Checklist

Before considering this feature complete, verify:

- [ ] Profile page displays at `/profiles/` route
- [ ] Centered card layout with 600px max-width
- [ ] Circular avatar with blue→green gradient (100px desktop, 80px mobile)
- [ ] White uppercase initials in avatar (36px desktop, 28px mobile)
- [ ] Username displayed below avatar (bold, 28px desktop, 24px mobile)
- [ ] Email displayed as subtitle (gray, 16px desktop, 14px mobile)
- [ ] Horizontal divider between header and info
- [ ] Data table shows all user fields correctly
- [ ] Table uses existing `.data-list` styling
- [ ] Responsive design works on mobile (tested at 375px width)
- [ ] No CSS conflicts with other pages
- [ ] No console errors or warnings
- [ ] All commits follow conventional commit format
- [ ] Design matches approved specification

---

## Troubleshooting Guide

**Issue: Avatar doesn't show gradient**
- Check CSS variables in `base.css` (--primary-clr, --serravalle-light-green-clr)
- Verify browser supports linear-gradient
- Check browser DevTools for CSS syntax errors

**Issue: Initials don't display**
- Verify template uses correct filter: `{{ user.username|slice:":2"|upper }}`
- Check user object has username attribute
- Inspect element in DevTools to see rendered HTML

**Issue: Card not centered**
- Check `.profile-page-wrapper` has `display: flex` and `justify-content: center`
- Verify no conflicting CSS from other files
- Check browser width is sufficient (> 600px for desktop view)

**Issue: Mobile layout broken**
- Verify responsive CSS is inside `@media(max-width: 800px)` block
- Check closing braces are correctly placed
- Test at various screen widths (320px, 375px, 768px)

**Issue: Data table styling incorrect**
- Confirm `.data-list` class is on table element
- Check existing `.data-list` styles weren't modified
- Verify table structure matches specification

---

## Next Steps (Future Enhancements)

After this implementation is complete, consider:

1. **Add edit functionality** - Button to edit profile information
2. **Add change password link** - Security settings
3. **Add stats card** - Show user activity statistics
4. **Add recent activity** - Timeline of recent reports/inspections
5. **Profile picture upload** - Replace initials with actual photo
6. **User preferences** - Language, timezone, notification settings
7. **Two-factor authentication** - Security badge/settings

These are NOT part of this implementation plan but are documented for future reference.

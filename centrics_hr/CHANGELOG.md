# Changelog

All notable changes to the Centrics HR module will be documented in this file.

## [16.0.1.0.0] - 2025-12-26

### Added
- Enhanced name management fields for employees:
  - Initials of the Name field
  - First Name field
  - Middle Name field
  - Last Name field
- Employee approval workflow system
  - Draft, Waiting, Approved, and Rejected states
  - Send for Approval functionality
  - Approve/Reject actions with email notifications
  - Reset to Draft capability
- Automatic employee number generation
  - Configurable at company level
  - Sequential numbering using IR sequence
- Retirement planning features
  - Retirement date auto-calculation based on birthday and company retirement age
  - Joined date tracking
- Company-level configurations
  - Employee approval workflow toggle
  - Automatic employee number generation toggle
  - Retirement age setting
- Pending Employees menu for approvers
  - Filtered view showing only employees awaiting approval
  - Assigned to specific approver
- Email notifications
  - Notification when profile sent for approval
  - Notification on approval
  - Notification on rejection with reason
- Employee profile rejection wizard
  - Capture rejection reason
  - Send notification with reason to requester

### Changed
- Made Job Position, Mobile Phone, and Work Email mandatory fields
- Employee records are inactive by default when approval workflow is enabled
- Employee number can be read-only when auto-generation is enabled

### Technical
- Extended hr.employee model with additional fields and methods
- Extended res.company model with HR configuration fields
- Extended res.config.settings for company HR settings
- Created onboarding checklist system for new employee onboarding
- Implemented state-based workflow with proper transitions

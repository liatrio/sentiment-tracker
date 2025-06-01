# Sentiment Tracker Bot - Product Requirements Document

## Overview
The Sentiment Tracker is a Slack bot designed to collect, analyze, and report team sentiment. It allows team members to provide feedback on their work experience, which is then anonymized, analyzed using AI, and reported back to the team channel.

## Core Requirements

### 1. Feedback Collection
- **Trigger Mechanism**: Any team member can initiate feedback collection via Slack command
- **Command Syntax**: 
  - `@sentiment-bot gather feedback for @team-group-name` (uses default time window)
  - `@sentiment-bot gather feedback for @team-group-name in X minutes` (custom time window)
- **Time Window**:
  - Default: 5-minute collection window
  - Custom: User-specified duration
  - Reminder: Bot sends a reminder message 1 minute before the window closes
  - Cutoff: Only responses received within the time window are included

### 2. Feedback Questions
The MVP will include three fixed questions:
1. "How are you feeling about this week?" (Scale 1-3, using emojis 😊 😐 😟)
2. "What went well this week?"
3. "What could have gone better?"

The architecture should support future customization of questions.

### 3. User Interface
- **Collection Method**: Slack modal dialog
- **Question Format**:
  - Sentiment question: Emoji buttons (😊 😐 😟)
  - Open-ended questions: Text input fields
- **Modal Design**: Single modal containing all three questions

### 4. Report Generation
- **Delivery**: Report sent back to the original channel where the bot was called
- **Content**:
  - Summary of overall team sentiment (based on emoji responses)
  - Key themes identified from qualitative responses
  - Anonymized quotes (rewritten by AI to standardize style and further mask identity)
  - Visual representation of overall mood using emojis
- **Templates**: Basic customization with preset options:
  - Comprehensive (all data points)
  - Brief summary (highlights only)
  - Focus on improvements
- **Low Response Handling**: Generate report anyway but note the low response rate

## Technical Specifications

### 1. Architecture
- **Framework**: Bolt for Python (building on existing Slackbot project)
- **Deployment**: Containerized for deployment in in-house Kubernetes cluster
- **Multi-team Support**: Must handle multiple teams using the bot simultaneously
- **Scaling**: Single instance with vertical scaling if needed

### 2. In-Memory Data Management
- **Storage Approach**: Thread-safe in-memory dictionary
- **Data Structure**:
  - Simple dictionary with session IDs as keys
  - Each session contains: team members, responses received, time window information
- **Session Management**:
  - Maximum concurrent sessions: 50 (configurable via environment variables)
  - Automatic cleanup of sessions older than 24 hours (configurable)
  - Cleanup check triggered when new sessions are created
- **Concurrency Implementation**:
  - Shared dictionary protected by locks for thread safety
  - Each feedback collection session runs in its own worker thread
  - Main application thread handles incoming requests
  - Thread-safe callbacks update the shared memory store when responses arrive
  - Non-blocking timer implementation using scheduled tasks/callbacks
- **Persistence**: 
  - No persistence across application restarts
  - Users must restart feedback collection if application restarts
  - Reports are stored in Slack message history only
- **Configuration**: All settings managed via environment variables

### 3. AI Integration
- **Provider**: OpenAI
- **Use Cases**:
  - Sentiment analysis of textual responses
  - Theme identification from qualitative feedback
  - Quote anonymization and standardization
  - Summary generation for reports
- **Implementation**:
  - API integration with appropriate rate limiting and error handling
  - Prompt engineering for consistent results
  - Fallback mechanism: If OpenAI is unavailable, report raw data without AI analysis

### 4. Security & Privacy
- **Access Control**: For MVP, any team member can trigger sentiment collection
- **Data Privacy**:
  - All individual feedback anonymized in reports
  - No persistent storage of user responses
  - AI-based rewriting of quotes to further mask identity
- **Data Handling**: All data cleared from memory after report generation

## Implementation Details

### 1. Slack Integration
- **Bot Permissions Required**:
  - `chat:write` - Send messages
  - `users:read` - Access user information
  - `usergroups:read` - Access user group information
  - `im:write` - Send direct messages
  - `commands` - Create slash commands
  - `views:write` - Open and update modals
- **Event Subscriptions**:
  - `message.channels` - Listen for messages in channels
  - `message.im` - Listen for direct messages
- **Interactive Components**:
  - Button actions for emoji selection
  - Modal submission for feedback

### 2. Workflow
1. User triggers bot with command in a channel
2. Bot identifies members of the specified user group
3. Bot sends DM with modal to each member
4. Bot tracks responses and sends reminder before deadline
5. At deadline, bot processes all received feedback
6. Bot uses OpenAI to analyze sentiment, identify themes, and anonymize quotes
7. Bot generates and posts report to the original channel
8. Bot clears session data from memory

### 3. Error Handling
- **Approach**: Cancel the sentiment thread for the session and write back to the channel with error information
- **Notification Levels**:
  - Critical errors: Notify in channel where bot was triggered
  - Minor issues: Log without user disruption
- **Specific Error Scenarios**:
  - API rate limits: Cancel session and notify channel
  - User not found: Cancel session and notify channel
  - OpenAI API unavailable: Report raw data without AI analysis

### 4. Performance Considerations
- **Concurrency**:
  - Handle multiple concurrent feedback sessions (up to configured limit)
  - Support teams of various sizes (5-500+ members)
  - Thread synchronization with minimal locking to prevent contention
  - Worker threads for session management to prevent blocking main thread
  - Efficient resource utilization through non-blocking timer implementation
- **Latency**:
  - Modal response time < 1 second
  - Report generation < 30 seconds after deadline
- **Resource Usage**:
  - Memory usage controlled via session limits and cleanup
  - Basic logging for monitoring
  - Thread pool management to prevent resource exhaustion

## Installation & Documentation

### 1. Installation
- One-click installation from Slack App Directory
- Configuration options documented for admin setup

### 2. Documentation
- **In-app Help**:
  - `@sentiment-bot help` command for basic instructions
  - Contextual help in modals
- **External Documentation**:
  - Setup guide
  - User guide
  - Admin guide
  - API documentation (for future integrations)

## Testing Plan

### 1. Unit Testing
- Test all core functions independently
- Mock external services (Slack API, OpenAI)
- Aim for >80% code coverage

### 2. Integration Testing
- Test interaction between components
- Test thread safety and concurrency
- Test API integrations with real credentials in test environment

### 3. End-to-End Testing
- Complete workflow testing
- Performance testing under load
- Security testing

### 4. User Acceptance Testing
- Internal team testing before release
- Feedback collection from early adopters

## Monitoring & Analytics

### 1. System Monitoring
- Basic logging for MVP
- Future enhancement: OpenTelemetry integration
- Error rates and types

### 2. Usage Analytics
- Number of feedback sessions
- Response rates
- Question completion rates
- Report viewing metrics

## Future Enhancements (Post-MVP)

### 1. Feature Enhancements
- Customizable questions
- Scheduled/recurring feedback collection
- Advanced analytics and visualizations
- Team-specific configuration options

### 2. Technical Enhancements
- More sophisticated AI analysis
- Integration with other platforms (MS Teams, etc.)
- Export functionality for reports
- API for external integrations
- Enhanced monitoring with OpenTelemetry

## Development Timeline

### Phase 1: Core Functionality (MVP)
- Slack command processing
- Modal UI implementation
- Basic feedback collection
- OpenAI integration
- Simple report generation

### Phase 2: Refinement
- Enhanced report templates
- Improved analytics
- UI polish
- Performance optimization

### Phase 3: Advanced Features
- Customizable questions
- Scheduled collection
- Advanced visualizations
- External integrations

## Success Metrics
- User adoption rate
- Feedback response rate
- Report usefulness (survey)
- Team sentiment improvement over time

---

This PRD is a living document and may be updated as requirements evolve during the development process.

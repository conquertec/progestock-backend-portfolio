#!/bin/bash
# Safe deployment script with built-in checks
# Usage: ./scripts/deploy.sh [staging|production]

set -e

ENVIRONMENT=${1:-staging}
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 ProGestock Deployment Script${NC}"
echo "=================================="
echo ""

# Function to check if on correct branch
check_branch() {
    CURRENT_BRANCH=$(git branch --show-current)

    if [ "$ENVIRONMENT" = "production" ]; then
        if [ "$CURRENT_BRANCH" != "main" ]; then
            echo -e "${RED}❌ Error: Must be on 'main' branch to deploy to production${NC}"
            echo "Current branch: $CURRENT_BRANCH"
            exit 1
        fi
    elif [ "$ENVIRONMENT" = "staging" ]; then
        if [ "$CURRENT_BRANCH" != "staging" ]; then
            echo -e "${RED}❌ Error: Must be on 'staging' branch to deploy to staging${NC}"
            echo "Current branch: $CURRENT_BRANCH"
            exit 1
        fi
    fi
}

# Function to run tests
run_tests() {
    echo -e "${YELLOW}🧪 Running tests...${NC}"
    python manage.py test --verbosity=2

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ All tests passed${NC}"
    else
        echo -e "${RED}❌ Tests failed! Deployment aborted.${NC}"
        exit 1
    fi
}

# Function to check migrations
check_migrations() {
    echo -e "${YELLOW}🔍 Checking for unapplied migrations...${NC}"

    # Check if there are new migrations
    if python manage.py makemigrations --check --dry-run > /dev/null 2>&1; then
        echo -e "${GREEN}✅ No migration issues detected${NC}"
    else
        echo -e "${YELLOW}⚠️  Warning: There may be new migrations${NC}"
        echo "Have you tested migrations on staging?"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Deployment aborted."
            exit 1
        fi
    fi
}

# Function to check for uncommitted changes
check_uncommitted() {
    if ! git diff-index --quiet HEAD --; then
        echo -e "${RED}❌ Error: You have uncommitted changes${NC}"
        echo "Please commit or stash your changes before deploying."
        exit 1
    fi
    echo -e "${GREEN}✅ No uncommitted changes${NC}"
}

# Function to confirm production deployment
confirm_production() {
    if [ "$ENVIRONMENT" = "production" ]; then
        echo ""
        echo -e "${RED}⚠️  PRODUCTION DEPLOYMENT WARNING ⚠️${NC}"
        echo "This will deploy to production and affect your 4 active users!"
        echo ""
        echo "Pre-deployment checklist:"
        echo "  - Have you tested on staging? (staging environment)"
        echo "  - Are all tests passing?"
        echo "  - Have you checked the Railway staging logs?"
        echo "  - Are there any breaking changes?"
        echo "  - Is the team aware of this deployment?"
        echo ""
        read -p "Are you sure you want to deploy to PRODUCTION? (yes/NO) " -r
        echo
        if [[ ! $REPLY =~ ^yes$ ]]; then
            echo "Deployment aborted."
            exit 1
        fi
    fi
}

# Main deployment flow
main() {
    echo "Target environment: $ENVIRONMENT"
    echo ""

    # Run checks
    check_branch
    check_uncommitted
    run_tests
    check_migrations
    confirm_production

    # Deploy
    echo ""
    echo -e "${GREEN}🚀 Deploying to $ENVIRONMENT...${NC}"

    git pull origin $(git branch --show-current)
    git push origin $(git branch --show-current)

    echo ""
    echo -e "${GREEN}✅ Deployment initiated!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Wait 3-5 minutes for deployment to complete"

    if [ "$ENVIRONMENT" = "staging" ]; then
        echo "2. Check staging environment"
        echo "3. Review Railway staging logs: railway logs"
        echo "4. Test all critical features"
        echo "5. If good, deploy to production: ./scripts/deploy.sh production"
    else
        echo "2. Check production environment"
        echo "3. Review Railway logs: railway logs"
        echo "4. Monitor for errors for 10 minutes"
        echo "5. Test critical paths: login, invoice, email"
        echo "6. Have rollback plan ready"
    fi
}

# Run main function
main

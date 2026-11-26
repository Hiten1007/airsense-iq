pipeline {
    agent any

    environment {
        IMAGE_NAME = 'airsense-iq'
        PORT = '8000'
    }

    stages {
        stage('1. Checkout Repository') {
            steps {
                echo 'Checking out source code from Git...'
                checkout scm
            }
        }

        stage('2. Dependencies & Environment Setup') {
            steps {
                echo 'Installing Python3, Docker CLI, and setting up virtual environment...'
                sh '''
                    # Install Python3 and Docker CLI if not present (Jenkins container is Debian-based)
                    if ! command -v python3 > /dev/null 2>&1 || ! command -v docker > /dev/null 2>&1; then
                        apt-get update -qq && apt-get install -y -qq python3 python3-pip python3-venv docker-cli
                    fi
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    mkdir -p reports
                '''
            }
        }

        stage('3. Static Code Analysis (Bandit & Flake8)') {
            steps {
                echo 'Executing Static Application Security Testing (SAST)...'
                sh '''
                    . venv/bin/activate
                    echo "--- Flake8 Quality & Syntax Verification ---"
                    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=venv,build,dist,.git
                    flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics --exclude=venv,build,dist,.git

                    echo "--- Bandit Security Vulnerability Scanner ---"
                    python -m bandit -r src/ -f custom --msg-template "{abspath}:{line}: {test_id}[bandit]: {severity}: {msg}"
                    python -m bandit -r src/ -f json -o reports/bandit-report.json || true
                '''
            }
        }

        stage('4. Dependency Vulnerability Audit') {
            steps {
                echo 'Checking installed environment dependencies against CVE Advisory Databases...'
                sh '''
                    . venv/bin/activate
                    python -m pip_audit --local --format json -o reports/pip-audit-report.json || true
                    python -m pip_audit --local
                '''
            }
        }

        stage('5. Automated Unit & Integration Tests') {
            steps {
                echo 'Running full Pytest test suite...'
                sh '''
                    . venv/bin/activate
                    PYTHONPATH=. pytest -v tests/ --junitxml=reports/test-results.xml
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/test-results.xml'
                }
            }
        }

        stage('6. Docker Containerization') {
            steps {
                echo "Packaging container image: ${IMAGE_NAME}:${BUILD_NUMBER}..."
                sh '''
                    docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} -t ${IMAGE_NAME}:latest .
                '''
            }
        }

        stage('7. Container Security Audit (Trivy)') {
            steps {
                echo 'Scanning container image for OS and library CVEs...'
                sh '''
                    if command -v trivy >/dev/null 2>&1; then
                        trivy image --severity HIGH,CRITICAL --format table ${IMAGE_NAME}:latest || true
                    else
                        echo "Trivy not installed in environment; skipping container CVE scan step."
                    fi
                '''
            }
        }

        stage('8. Automated Continuous Deployment') {
            steps {
                echo 'Executing automated deployment stage...'
                sh '''
                    if [ -n "$DEPLOY_HOOK_URL" ]; then
                        echo "Calling Render deployment webhook..."
                        curl -X POST "$DEPLOY_HOOK_URL"
                    else
                        echo "DEPLOY_HOOK_URL not configured. Image ${IMAGE_NAME}:latest packaged and verified locally."
                    fi
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
        success {
            echo "✅ Jenkins Pipeline successfully completed for Build #${BUILD_NUMBER}!"
        }
        failure {
            echo "❌ Jenkins Pipeline failed for Build #${BUILD_NUMBER}. Please inspect reports and console log."
        }
    }
}

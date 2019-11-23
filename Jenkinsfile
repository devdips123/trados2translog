def count = ""
pipeline {
    agent any
    parameters {
        string(name: "docker_port", defaultValue: "8000", description: "Port for the container")
        string(name: "image_version", defaultValue: "1.0", description: "Version of the docker image")
		string(name: "container_name", defaultValue: "trados2translog", description: "Name of the container")
    }
    environment {
        NAME="Debasish"
        delete = "yes"
    }
    stages {
        stage('source code') {
           
            steps {
                git 'https://github.com/devdips123/trados2translog.git'
                script {
                    if (!fileExists("Dockerfile")) {
                        error('Dockerfile missing.')
                    } else {
                        echo "Found Dockerfile!!"
                    }
                }
            }
        }
        stage('build') {
            steps {
                sh "docker build -t trados:${params.image_version} ."
            }
        }
        
        stage('docker run') {
            steps {
                sh "docker run --name ${params.container_name} -p ${params.docker_port}:8000 -d trados:1.0"
            }
        }
        stage('result') {
            steps {
                script{
                count = sh (script: "docker ps -f name=${params.container_name} | grep -v 'IMAGE' | wc -l ", returnStdout: true).trim()
                echo "Build ID: ${env.BUILD_ID}, Node Name: ${env.NODE_NAME}, Build Number: ${env.BUILD_NUMBER}"
				echo "count = ${count}"
				sh "curl -X GET localhost:${params.docker_port}"
                }
            }
        }
		stage('tear down') {
		    when {
				    expression { count != '' }
				}
			steps {
				script {
					echo "Removing docker with count = $count"
					sh "docker stop ${params.container_name}"
					sh "docker rm ${params.container_name}"
				}
			}
        }
	}
}

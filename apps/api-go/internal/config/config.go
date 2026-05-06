package config

import "os"

type Settings struct {
	Host             string
	Port             string
	DatabaseURL      string
	AgentWorkerURL   string
	AgentWorkerToken string
}

func Load() Settings {
	return Settings{
		Host:             readEnv("HOST", "0.0.0.0"),
		Port:             readEnv("PORT", "8080"),
		DatabaseURL:      os.Getenv("DATABASE_URL"),
		AgentWorkerURL:   readEnv("AGENT_WORKER_URL", "http://127.0.0.1:8090"),
		AgentWorkerToken: os.Getenv("AGENT_WORKER_TOKEN"),
	}
}

func (settings Settings) HTTPAddress() string {
	return settings.Host + ":" + settings.Port
}

func readEnv(name string, fallback string) string {
	value := os.Getenv(name)
	if value == "" {
		return fallback
	}
	return value
}

package domain

type RunEventListResponse struct {
	Items []RunEventRecord `json:"items"`
	Page  PageInfo         `json:"page"`
}

type RunTurnListResponse struct {
	Items []RunTurnRecord `json:"items"`
	Page  PageInfo        `json:"page"`
}

type RunToolCallListResponse struct {
	Items []RunToolCallRecord `json:"items"`
	Page  PageInfo            `json:"page"`
}

type LLMCallListResponse struct {
	Items []LLMCallRecord `json:"items"`
	Page  PageInfo        `json:"page"`
}


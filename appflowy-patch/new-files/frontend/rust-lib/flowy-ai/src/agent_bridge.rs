use serde::{Deserialize, Serialize};
use reqwest::Client;
use flowy_error::{FlowyError};
use std::collections::HashMap;

#[derive(Debug, Serialize, Deserialize)]
pub struct AgentRequest {
    pub prompt: String,
    pub context: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AgentResponse {
    pub thought: String,
    pub actions: Vec<serde_json::Value>,
}

pub async fn execute_agent(
    prompt: String,
    context: HashMap<String, serde_json::Value>,
) -> Result<AgentResponse, FlowyError> {
    let client = Client::new();
    let res = client
        .post("http://localhost:8000/agent/execute")
        .json(&AgentRequest { prompt, context })
        .send()
        .await
        .map_err(|e| FlowyError::internal().with_context(e.to_string()))?;

    let response = res
        .json::<AgentResponse>()
        .await
        .map_err(|e| FlowyError::internal().with_context(e.to_string()))?;

    Ok(response)
}

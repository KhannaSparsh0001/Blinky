use super::Tool;
use crate::providers::ToolDefinition;
use anyhow::{Context, Result};
use async_trait::async_trait;
use reqwest::Client;
use serde_json::{json, Value};
use std::time::Duration;

pub struct CryptoPriceTool {
    client: Client,
}

impl CryptoPriceTool {
    pub fn new() -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(10))
            .build()
            .unwrap_or_default();
        Self { client }
    }
}

#[async_trait]
impl Tool for CryptoPriceTool {
    fn definition(&self) -> ToolDefinition {
        ToolDefinition {
            name: "find_crypto_price".to_string(),
            description: "Get the current market price and 24h change for a cryptocurrency symbol (e.g. 'BTC', 'ETH', 'SOL')".to_string(),
            parameters: json!({
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Cryptocurrency ticker symbol (e.g. 'BTC', 'ETH', 'SOL', 'DOGE')"
                    }
                },
                "required": ["symbol"]
            }),
        }
    }

    async fn execute(&self, args: Value) -> Result<Value> {
        let symbol = args
            .get("symbol")
            .and_then(|v| v.as_str())
            .unwrap_or("BTC")
            .to_uppercase();

        let pair = format!("{}USDT", symbol);
        let url = format!("https://api.binance.com/api/v3/ticker/24hr?symbol={}", pair);

        let res = self.client.get(&url).send().await;
        if let Ok(resp) = res {
            if resp.status().is_success() {
                if let Ok(data) = resp.json::<Value>().await {
                    let last_price = data["lastPrice"].as_str().unwrap_or("0");
                    let price_change_percent = data["priceChangePercent"].as_str().unwrap_or("0");
                    let high_price = data["highPrice"].as_str().unwrap_or("0");
                    let low_price = data["lowPrice"].as_str().unwrap_or("0");

                    return Ok(json!({
                        "symbol": symbol,
                        "pair": pair,
                        "price_usd": last_price,
                        "change_24h_percent": price_change_percent,
                        "high_24h": high_price,
                        "low_24h": low_price,
                    }));
                }
            }
        }

        anyhow::bail!("Failed to fetch crypto price for {}", symbol)
    }
}

pub struct WikipediaTool {
    client: Client,
}

impl WikipediaTool {
    pub fn new() -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(10))
            .build()
            .unwrap_or_default();
        Self { client }
    }
}

#[async_trait]
impl Tool for WikipediaTool {
    fn definition(&self) -> ToolDefinition {
        ToolDefinition {
            name: "lookup_wikipedia".to_string(),
            description: "Look up a summary and overview of a person, concept, historical event, or technology on Wikipedia".to_string(),
            parameters: json!({
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Topic or entity name to search on Wikipedia"
                    }
                },
                "required": ["query"]
            }),
        }
    }

    async fn execute(&self, args: Value) -> Result<Value> {
        let query = args.get("query").and_then(|v| v.as_str()).unwrap_or("");
        let encoded = urlencoding::encode(query);
        let url = format!("https://en.wikipedia.org/api/rest_v1/page/summary/{}", encoded);

        let resp = self
            .client
            .get(&url)
            .header("User-Agent", "FlickyAgent/1.0 (https://github.com/NousResearch/Blinky)")
            .send()
            .await
            .context("Failed to connect to Wikipedia API")?;

        if !resp.status().is_success() {
            anyhow::bail!("Wikipedia page not found for '{}'", query);
        }

        let body: Value = resp.json().await.context("Failed to parse Wikipedia JSON response")?;

        let title = body["title"].as_str().unwrap_or(query);
        let extract = body["extract"].as_str().unwrap_or("No summary available");
        let page_url = body["content_urls"]["desktop"]["page"].as_str().unwrap_or("");

        Ok(json!({
            "title": title,
            "extract": extract,
            "url": page_url
        }))
    }
}

pub struct CreateSpreadsheetTool;

impl CreateSpreadsheetTool {
    pub fn new() -> Self {
        Self
    }
}

#[async_trait]
impl Tool for CreateSpreadsheetTool {
    fn definition(&self) -> ToolDefinition {
        ToolDefinition {
            name: "create_spreadsheet".to_string(),
            description: "Go to Google Docs / Google Sheets and create or open a spreadsheet".to_string(),
            parameters: json!({
                "type": "object",
                "properties": {
                    "target_url": {
                        "type": "string",
                        "description": "Optional specific Google Sheets URL to open"
                    },
                    "topic": {
                        "type": "string",
                        "description": "Subject or purpose of the spreadsheet (e.g. 'monthly budget', 'student grades')"
                    },
                    "columns": {
                        "type": "array",
                        "items": { "type": "string" },
                        "description": "Optional list of column header names"
                    }
                }
            }),
        }
    }

    async fn execute(&self, args: Value) -> Result<Value> {
        let topic = args.get("topic").and_then(|v| v.as_str()).unwrap_or("spreadsheet");
        let columns = args.get("columns").and_then(|v| v.as_array());

        let raw_url = args
            .get("target_url")
            .or_else(|| args.get("url"))
            .and_then(|v| v.as_str())
            .unwrap_or("https://docs.google.com/spreadsheets/u/0/");

        let url = if raw_url.contains("sheets.new") || raw_url.is_empty() {
            "https://docs.google.com/spreadsheets/u/0/"
        } else {
            raw_url
        };

        #[cfg(target_os = "windows")]
        let _ = std::process::Command::new("cmd").args(["/C", "start", "", url]).spawn();
        #[cfg(target_os = "linux")]
        let _ = std::process::Command::new("xdg-open").arg(url).spawn();
        #[cfg(target_os = "macos")]
        let _ = std::process::Command::new("open").arg(url).spawn();

        let message = format!("Opened Google Spreadsheet at {}", url);

        Ok(json!({
            "success": true,
            "url": url,
            "topic": topic,
            "columns": columns,
            "message": message
        }))
    }
}

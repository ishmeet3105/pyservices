import requests
import time
import pandas as pd
from app.config import HASURA_URL, HASURA_HEADERS
from typing import List, Dict


def fetch_unparsed_prospects(prospect_id):
    query = """
    query FetchProspects($prospect_id: uuid!) {
      vocallabs_prospects(
        where: {
          prospect_group_id: { _eq: $prospect_id }
        },
        order_by: { created_at: asc }
      ) {
        id
        name
        phone
        data
      }
    }
    """
    variables = {"prospect_id": prospect_id}
    response = requests.post(
        HASURA_URL,
        headers=HASURA_HEADERS,
        json={"query": query, "variables": variables}
    )
    response.raise_for_status()
    data = response.json()
    return pd.DataFrame(data["data"]["vocallabs_prospects"])


def update_prospect_name(prospect_id, devanagari_name):
    mutation = """
    mutation UpdateProspect($name: String!, $id: uuid!) {
      update_vocallabs_prospects(
        where: {id: {_eq: $id}}, 
        _set: {name: $name}
      ) {
        affected_rows
      }
    }
    """
    variables = {"name": devanagari_name, "id": prospect_id}

    try:
        response = requests.post(
            HASURA_URL,
            headers=HASURA_HEADERS,
            json={"query": mutation, "variables": variables}
        )
        response.raise_for_status()
        return response.json()["data"]["update_vocallabs_prospects"]["affected_rows"]
    except Exception as e:
        print(f"Error updating {prospect_id}: {e}")
        return 0



def fetch_autostart_campaigns():
    query = """
    {
  vocallabs_campaigns(where: {campaign_lock: {_eq: true}, autostart: {_eq: true}}) {
    id
    client_id
    start_time
    end_time
    active
    campaign_lock
  }
}

    """
    try:
        print("📡 Sending request to Hasura...")
        start_time = time.time()
        response = requests.post(
            HASURA_URL,
            headers=HASURA_HEADERS,
            json={"query": query}
        )
        response.raise_for_status()
        data = response.json()
        campaigns = data.get("data", {}).get("vocallabs_campaigns", [])
        if not campaigns:
            return []
        return campaigns
    except Exception as e:
        print(f"Error fetching campaigns: {e}")
        return None

def update_campaign_active_status(campaign_id, active):
    mutation = """
    mutation UpdateCampaignStatus($id: uuid!, $active: Boolean!) {
      update_vocallabs_campaigns_by_pk(pk_columns: {id: $id}, _set: {active: $active}) {
        id
        active
      }
    }
    """
    variables = {
        "id": campaign_id,
        "active": active
    }
    try:
        response = requests.post(
            HASURA_URL,
            headers=HASURA_HEADERS,
            json={"query": mutation, "variables": variables}
        )
        response.raise_for_status()
        return response.json()["data"]["update_vocallabs_campaigns_by_pk"]
    except Exception as e:
        print(f"Error updating campaign {campaign_id}: {e}")
        return None

def get_agent_prompt_and_count(agent_id: str):
    query = """
    query AgentAggregatePrompts($_eq: uuid!) {
      vocallabs_agent(where: {id: {_eq: $_eq}}) {
        calls_aggregate(where: {call_status: {_eq: "completed"}}) {
          aggregate {
            count
          }
        }
        agent_post_data_collections {
          prompt
          key
        }
      }
    }
    """
    variables = {"_eq": agent_id}
    response = requests.post(
        HASURA_URL,
        headers=HASURA_HEADERS,
        json={"query": query, "variables": variables}
    )
    response.raise_for_status()
    return response.json()["data"]["vocallabs_agent"][0]

def get_calls_by_batch(agent_id: str, gte: str, lte: str, offset: int, limit: int, is_premium: bool):
    if is_premium:
        query = """
        query CallBatchPremium($_eq: uuid!, $_gte: timestamptz!, $_lte: timestamptz!, $offset: Int!, $limit: Int!) {
          vocallabs_calls(
            where: {agent_id: {_eq: $_eq}, created_at: {_gte: $_gte, _lte: $_lte}},
            limit: $limit,
            offset: $offset
          ) {
            call_id
            call_messages {
              role
              content
            }
          }
        }
        """
    else:
        query = """
        query CallBatchNonPremium($_eq: uuid!, $_gte: timestamptz!, $_lte: timestamptz!, $offset: Int!, $limit: Int!) {
          vocallabs_calls(
            where: {agent_id: {_eq: $_eq}, created_at: {_gte: $_gte, _lte: $_lte}},
            limit: $limit,
            offset: $offset
          ) {
            call_id
            post_call_transcript
          }
        }
        """

    variables = {
        "_eq": agent_id,
        "_gte": gte,
        "_lte": lte,
        "offset": offset,
        "limit": limit
    }

    response = requests.post(
        HASURA_URL,
        headers=HASURA_HEADERS,
        json={"query": query, "variables": variables}
    )
    response.raise_for_status()
    return response.json()["data"]["vocallabs_calls"]



def insert_multiple_call_data(entries: List[Dict]):
    mutation = """
    mutation InsertMany($objects: [vocallabs_call_data_insert_input!]!) {
      insert_vocallabs_call_data(
        objects: $objects,
        on_conflict: {
          constraint: call_data_call_id_key_key,
          update_columns: value
        }
      ) {
        affected_rows
      }
    }
    """
    variables = {"objects": entries}

    response = requests.post(
        HASURA_URL,
        headers=HASURA_HEADERS,
        json={"query": mutation, "variables": variables}
    )
    response.raise_for_status()
    return response.json()


def fetch_call_ids_by_agent(agent_id: str):
    query = """
    query MyQuery($_eq: uuid = "") {
  vocallabs_call_message(where: {call: {agent_id: {_eq: $_eq}, call_status: {_eq: "completed"}}}) {
    call_id
  }
}

    """
    variables = {"_eq": agent_id}
    response = requests.post(
        HASURA_URL,
        headers=HASURA_HEADERS,
        json={"query": query, "variables": variables}
    )
    return response.json()


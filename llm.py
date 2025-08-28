from typing import Dict, Optional, Any, List, Union
import json
from abc import ABC, abstractmethod
from openai import OpenAI
from ollama import chat, Client
import logging
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import Config

log = logging.getLogger(__name__)

class BaseLLMController(ABC):
    @abstractmethod
    def _prepare_messages(
        self, prompt: Union[str], images: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Prepares the message list in the format required by the specific API.
        This must be implemented by each subclass.
        """
        pass

    @abstractmethod
    def get_completion(self, prompt: Union[str]) -> str:
        """Get completion from LLM."""
        pass

    @abstractmethod
    def get_json_completion(
        self,
        prompt: Union[str],
        schema: BaseModel,
        images: Optional[List[str]] = None,
    ) -> dict:
        """Get structured JSON response from LLM using Pydantic schema."""
        pass


class OpenAIController(BaseLLMController):
    def __init__(
        self,
        llm_config: Optional[Config.LLMConfig] = None,
    ):
        self.model = (
            llm_config.model_name
            if llm_config and hasattr(llm_config, "model_name")
            else "gpt-4o-mini"
        )
        self.max_tokens = (
            llm_config.max_tokens
            if llm_config and hasattr(llm_config, "max_tokens")
            else 4000
        )
        self.temperature = (
            llm_config.temperature
            if llm_config and hasattr(llm_config, "temperature")
            else 0.7
        )
        base_url = (
            llm_config.api_base
            if llm_config and hasattr(llm_config, "api_base")
            else None
        )
        self.frequency_penalty = (
            llm_config.frequency_penalty
            if llm_config and hasattr(llm_config, "frequency_penalty")
            else 0.0
        )
        self.presence_penalty = (
            llm_config.presence_penalty
            if llm_config and hasattr(llm_config, "presence_penalty")
            else 0.0
        )

        if base_url is not None:
            self.client = OpenAI(api_key=llm_config.api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=llm_config.api_key)

    def _prepare_messages(
        self, prompt: Union[str], add_system_prompt: bool = True
    ) -> List[Dict[str, Any]]:
        """Prepares messages for the OpenAI API format."""
        if isinstance(prompt, object) and hasattr(prompt, 'storage'):
            res_dict = [msg.to_dict() for msg in prompt.storage]
            return res_dict

        messages = []
        if add_system_prompt:
            messages.append(
                {"role": "system", "content": "You are a helpful assistant."}
            )
        messages.append({"role": "user", "content": prompt})
        return messages

    def get_completion(
        self, prompt: Union[str], json_response: bool = False
    ) -> str:
        messages = self._prepare_messages(prompt)
        parameters = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
        }
        if json_response:
            parameters["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(**parameters)
        return response.choices[0].message.content

    def get_json_completion(
        self,
        prompt: Union[str],
        schema: BaseModel,
        images: Optional[list] = None,
    ) -> dict:
        """
        Get structured JSON response from OpenAI using Pydantic schema.
        :param prompt: str
        :param schema: Pydantic BaseModel
        :param images: Optional[list] = None
        :return: dict
        """
        try:
            if isinstance(prompt, object) and hasattr(prompt, 'storage'):
                # If it's a memory object, use its history.
                # We will attach images to the content of the *last* message.
                messages = [msg.to_dict() for msg in prompt.storage]
                last_content = messages[-1]["content"]

                content_list = [{"type": "text", "text": last_content}]
                if images:
                    for img_url in images:
                        content_list.append(
                            {"type": "image_url", "image_url": {"url": img_url}}
                        )
                messages[-1]["content"] = content_list

            else:  # It's a simple string prompt
                content_list = [{"type": "text", "text": prompt}]
                if images:
                    for img_url in images:
                        content_list.append(
                            {"type": "image_url", "image_url": {"url": img_url}}
                        )
                messages = [{"role": "user", "content": content_list}]

            completion = self.client.beta.chat.completions.parse(
                temperature=self.temperature,
                model=self.model,
                messages=messages,
                response_format=schema,
            )
            message = completion.choices[0].message
            if hasattr(message, "parsed") and message.parsed:
                return message.parsed
            elif hasattr(message, "refusal") and message.refusal:
                return {"refusal": message.refusal}
            else:
                return {}
        except Exception as e:
            logging.error(f"Error in OpenAIController.get_json_completion: {e}")
            return {}


class OllamaController(BaseLLMController):
    def __init__(self, llm_config: Optional[Config.LLMConfig] = None):
        self.model = (
            llm_config.model_name
            if llm_config and hasattr(llm_config, "model_name")
            else "llama3.1"
        )
        self.max_tokens = (
            llm_config.max_tokens
            if llm_config and hasattr(llm_config, "max_tokens")
            else 4000
        )
        self.temperature = (
            llm_config.temperature
            if llm_config and hasattr(llm_config, "temperature")
            else 0.7
        )
        self.frequency_penalty = (
            llm_config.frequency_penalty
            if llm_config and hasattr(llm_config, "frequency_penalty")
            else 0.0
        )
        self.presence_penalty = (
            llm_config.presence_penalty
            if llm_config and hasattr(llm_config, "presence_penalty")
            else 0.0
        )
        self.api_base = (
            llm_config.api_base
            if llm_config and hasattr(llm_config, "api_base")
            else None
        )
        self.api_key = (
            llm_config.api_key
            if llm_config and hasattr(llm_config, "api_key")
            else None
        )
        self.client = Client(host=self.api_base)

    def _prepare_messages(
        self, prompt: Union[str], add_system_prompt: bool = True
    ) -> List[Dict[str, Any]]:
        """Prepares messages for the Ollama API format."""
        if isinstance(prompt, object) and hasattr(prompt, 'get'):
            return prompt.get()

        messages = []
        if add_system_prompt:
            messages.append(
                {"role": "system", "content": "You are a helpful assistant."}
            )
        messages.append({"role": "user", "content": prompt})
        return messages

    def get_completion(
        self, prompt: Union[str], json_response: bool = False
    ) -> str:
        try:
            messages = self._prepare_messages(prompt)
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": self.temperature,
                    },
                think=False,
            )
            return response["message"]["content"]
        except Exception as e:
            logging.error(f"Error in OllamaController: {e}")
            return ""

    def get_json_completion(
        self,
        prompt: Union[str],
        schema: BaseModel,
        images: Optional[list] = None,
    ) -> dict:
        """
        Get structured JSON response from Ollama using Pydantic schema.
        :param prompt: str
        :param schema: Pydantic BaseModel
        :param images: Optional[list] = None
        :return: dict
        """
        try:
            messages = self._prepare_messages(prompt, add_system_prompt=False)

            if images:
                # Ollama expects images at the top level of the message dictionary
                messages[-1]["images"] = images
            response = chat(
                model=self.model,
                messages=messages,
                format=schema.model_json_schema(),  # 关键：传递schema
                options={
                    "temperature": 0,  # 更确定性
                    "num_predict": self.max_tokens,
                },
            )
            return schema.model_validate_json(response["message"]["content"])
        except Exception as e:
            logging.error(f"Error in OllamaController.get_json_completion: {e}")
            return {}


class LLM:
    """LLM-based controller for metadata generation"""

    def __init__(
        self,
        llm_config: Optional[Config.LLMConfig] = None,
    ):
        if llm_config is None:
            raise ValueError("Config must be provided")

        self.config = llm_config
        self.max_workers = getattr(llm_config, "max_workers", 4)
        backend = llm_config.backend
        if backend == "openai":
            self.llm = OpenAIController(llm_config=llm_config)
        elif backend == "ollama":
            self.llm = OllamaController(llm_config=llm_config)
        else:
            raise ValueError("Backend must be one of: 'openai', 'ollama'")

    def get_completion(
        self, prompt: Union[str], json_response: bool = False
    ) -> str:
        retry = 0
        max_retries = 3
        while retry < max_retries:
            try:
                return self.llm.get_completion(prompt, json_response)
            except Exception as e:
                print(f"Error getting completion: {e}")
                retry += 1
                if retry >= max_retries:
                    raise RuntimeError(
                        "Failed to get completion after multiple retries"
                    )
        # If we reach here, it means we failed to get a response after retries
        logging.error("Max retries reached, returning empty response.")
        # Log the error and return an empty string or handle it as needed
        logging.error(f"Error: {e}")
        logging.error("Returning empty response.")
        return ""

    def batch_get_completion(
        self, prompts: List[Union[str]], json_response: bool = False
    ) -> list:
        """ """
        results = [None] * len(prompts)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {
                executor.submit(self.get_completion, prompt, json_response): idx
                for idx, prompt in enumerate(prompts)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = f"Error: {e}"
        return results

    def get_json_completion(
        self,
        prompt: Union[str],
        schema: BaseModel,
        images: Optional[list] = None,
    ) -> dict:
        retry = 0
        max_retries = 3
        while retry < max_retries:
            try:
                return self.llm.get_json_completion(prompt, schema, images)
            except Exception as e:
                print(f"Error getting JSON completion: {e}")
                retry += 1
                if retry >= max_retries:
                    raise RuntimeError(
                        "Failed to get JSON completion after multiple retries"
                    )
        logging.error("Max retries reached, returning empty dict.")
        logging.error(f"Error: {e}")
        logging.error("Returning empty dict.")
        return {}

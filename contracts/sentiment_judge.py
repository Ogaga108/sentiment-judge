# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json

ERROR_EXPECTED = "[EXPECTED]"
ERROR_TRANSIENT = "[TRANSIENT]"
ERROR_LLM = "[LLM_ERROR]"

VALID_LABELS = ("positive", "negative", "neutral")


def _parse_llm_sentiment(raw) -> dict:
	if not isinstance(raw, dict):
		raise gl.vm.UserError(f"{ERROR_LLM} expected JSON object, got {type(raw).__name__}")
	label = None
	for key in ("label", "sentiment", "classification"):
		if key in raw and raw[key] is not None:
			label = str(raw[key]).strip().lower()
			break
	if label not in VALID_LABELS:
		raise gl.vm.UserError(
			f"{ERROR_LLM} label must be one of {VALID_LABELS}, got {label!r}"
		)
	score_raw = raw.get("score", raw.get("polarity"))
	try:
		score = int(round(float(str(score_raw).strip())))
	except (ValueError, TypeError, AttributeError):
		raise gl.vm.UserError(f"{ERROR_LLM} non-numeric score: {score_raw!r}")
	score = max(-100, min(100, score))
	confidence_raw = raw.get("confidence", 50)
	try:
		confidence = int(round(float(str(confidence_raw).strip())))
	except (ValueError, TypeError, AttributeError):
		confidence = 50
	confidence = max(0, min(100, confidence))
	reasoning = str(raw.get("reasoning", raw.get("explanation", "")))[:300]
	return {"label": label, "score": score, "confidence": confidence, "reasoning": reasoning}


class SentimentJudge(gl.Contract):
	"""On-chain sentiment analysis with validator consensus.

	Both the leader and every validator independently classify the text;
	the result is only accepted when they agree on the label and their
	scores are close enough.
	"""

	owner: Address
	results: TreeMap[str, str]
	total_analyses: u256

	def __init__(self):
		self.owner = gl.message.sender_address
		self.total_analyses = u256(0)

	def _analyze(self, text: str) -> dict:
		prompt = (
			"Analyze the sentiment of the text below.\n"
			f"Text: {text}\n\n"
			'Respond ONLY with JSON: {"label": "positive"|"negative"|"neutral", '
			'"score": <integer -100..100>, "confidence": <integer 0..100>, '
			'"reasoning": "<one short sentence>"}'
		)

		def leader_fn() -> dict:
			raw = gl.nondet.exec_prompt(prompt, response_format="json")
			return _parse_llm_sentiment(raw)

		def validator_fn(leaders_res: gl.vm.Result) -> bool:
			if not isinstance(leaders_res, gl.vm.Return):
				return False
			try:
				validator_result = leader_fn()
			except gl.vm.UserError:
				return False
			leader_label = leaders_res.calldata.get("label")
			leader_score = int(leaders_res.calldata.get("score", 0))
			if leader_label != validator_result["label"]:
				return False
			if abs(leader_score - validator_result["score"]) > 30:
				return False
			return True

		return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

	def _key(self, text: str) -> str:
		import hashlib

		normalized = " ".join(text.split()).strip().lower()
		return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

	@gl.public.write
	def analyze(self, text: str) -> dict:
		if len(text.strip()) < 3:
			raise gl.vm.UserError(f"{ERROR_EXPECTED} text too short (min 3 chars)")
		if len(text) > 8000:
			raise gl.vm.UserError(f"{ERROR_EXPECTED} text too long (max 8000 chars)")
		result = self._analyze(text)
		key = self._key(text)
		self.results[key] = json.dumps(result)
		self.total_analyses = self.total_analyses + u256(1)
		return {"key": key, **result}

	@gl.public.view
	def get_result(self, text: str) -> dict:
		key = self._key(text)
		raw = self.results.get(key)
		if raw is None:
			return {"exists": False}
		return {"exists": True, **json.loads(raw)}

	@gl.public.view
	def stats(self) -> dict:
		return {"total_analyses": int(self.total_analyses), "owner": str(self.owner)}

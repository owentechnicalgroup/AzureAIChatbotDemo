"""
Bank lookup service for mapping legal names to RSSD IDs.

Provides bank identification and lookup capabilities with fuzzy matching
to support natural language queries from AI agents.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import re
from difflib import SequenceMatcher

import structlog
from src.tools.base import BaseTool, ToolExecutionResult, ToolStatus
from .data_models import BankIdentification, BankSearchRequest

logger = structlog.get_logger(__name__).bind(log_type="SYSTEM")


class BankLookupTool(BaseTool):
    """
    Bank lookup tool for finding RSSD IDs from legal names.
    
    Provides fuzzy matching and search capabilities to help AI agents
    identify banks from natural language queries.
    """
    
    def __init__(self):
        """Initialize the bank lookup tool."""
        super().__init__(
            name="bank_lookup",
            description="Look up bank RSSD ID from legal name with fuzzy matching support"
        )
        
        # Load bank directory
        self.bank_directory = self._load_bank_directory()
        
        self.logger.info(
            "BankLookupTool initialized",
            banks_count=len(self.bank_directory)
        )
    
    def _load_bank_directory(self) -> List[BankIdentification]:
        """
        Load directory of banks with identification information.
        
        Returns:
            List of BankIdentification objects for known banks
        """
        # Mock bank directory with realistic but fake data
        # Using real bank names but fake/demo RSSD IDs for safety
        banks = [
            BankIdentification(
                legal_name="Wells Fargo Bank, National Association",
                rssd_id="451965",
                fdic_cert_id="3511",
                location="Sioux Falls, SD"
            ),
            BankIdentification(
                legal_name="JPMorgan Chase Bank, National Association", 
                rssd_id="480228",
                fdic_cert_id="628",
                location="Columbus, OH"
            ),
            BankIdentification(
                legal_name="Bank of America, National Association",
                rssd_id="541101", 
                fdic_cert_id="3510",
                location="Charlotte, NC"
            ),
            BankIdentification(
                legal_name="Citibank, National Association",
                rssd_id="628208",
                fdic_cert_id="7213", 
                location="Sioux Falls, SD"
            ),
            BankIdentification(
                legal_name="U.S. Bank National Association",
                rssd_id="504713",
                fdic_cert_id="6548",
                location="Cincinnati, OH"
            ),
            BankIdentification(
                legal_name="PNC Bank, National Association",
                rssd_id="817824",
                fdic_cert_id="6384",
                location="Wilmington, DE"
            ),
            BankIdentification(
                legal_name="Truist Bank",
                rssd_id="285815",
                fdic_cert_id="5501",
                location="Charlotte, NC"
            ),
            BankIdentification(
                legal_name="Goldman Sachs Bank USA",
                rssd_id="2182786", 
                fdic_cert_id="33124",
                location="Salt Lake City, UT"
            ),
            BankIdentification(
                legal_name="Capital One, National Association",
                rssd_id="112837",
                fdic_cert_id="4297",
                location="McLean, VA"
            ),
            BankIdentification(
                legal_name="TD Bank, National Association", 
                rssd_id="497404",
                fdic_cert_id="18409",
                location="Wilmington, DE"
            ),
            # Test/Demo banks
            BankIdentification(
                legal_name="Test Community Bank",
                rssd_id="123456",
                fdic_cert_id="12345",
                location="Test City, TS"
            ),
            BankIdentification(
                legal_name="Demo Regional Bank",
                rssd_id="654321",
                fdic_cert_id="54321", 
                location="Demo Town, DT"
            )
        ]
        
        return banks
    
    def _normalize_bank_name(self, name: str) -> str:
        """
        Normalize bank name for better matching.
        
        Args:
            name: Bank name to normalize
            
        Returns:
            Normalized bank name
        """
        # Convert to lowercase and remove common banking suffixes/prefixes
        normalized = name.lower().strip()
        
        # Remove common legal entity suffixes
        suffixes_to_remove = [
            ", national association",
            ", n.a.",
            " national association",
            " n.a.",
            ", national bank",
            " national bank", 
            ", n.b.",
            " n.b.",
            " bank",
            " corp",
            " corporation",
            " company",
            " co.",
            ", fsb",
            " fsb"
        ]
        
        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
        
        # Remove extra whitespace and punctuation
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _calculate_similarity(self, search_term: str, bank_name: str) -> float:
        """
        Calculate similarity score between search term and bank name.
        
        Args:
            search_term: User's search term
            bank_name: Bank name to compare against
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Normalize both names
        normalized_search = self._normalize_bank_name(search_term)
        normalized_bank = self._normalize_bank_name(bank_name)
        
        # Exact match gets highest score
        if normalized_search == normalized_bank:
            return 1.0
            
        # Check if search term is contained in bank name
        if normalized_search in normalized_bank:
            return 0.9
            
        # Check if bank name is contained in search term  
        if normalized_bank in normalized_search:
            return 0.85
            
        # Use sequence matching for fuzzy comparison
        similarity = SequenceMatcher(None, normalized_search, normalized_bank).ratio()
        
        # Boost score for word-level matches
        search_words = set(normalized_search.split())
        bank_words = set(normalized_bank.split())
        
        if search_words:
            word_overlap = len(search_words.intersection(bank_words)) / len(search_words)
            similarity = max(similarity, word_overlap * 0.8)
        
        return similarity
    
    def _search_banks(
        self, 
        search_term: str, 
        fuzzy_match: bool = True, 
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for banks matching the search term.
        
        Args:
            search_term: Search query
            fuzzy_match: Enable fuzzy matching
            max_results: Maximum results to return
            
        Returns:
            List of matching banks with similarity scores
        """
        if not search_term.strip():
            return []
        
        results = []
        
        for bank in self.bank_directory:
            # Calculate similarity score
            similarity = self._calculate_similarity(search_term, bank.legal_name)
            
            # Apply threshold based on fuzzy matching setting
            threshold = 0.3 if fuzzy_match else 0.8
            
            if similarity >= threshold:
                results.append({
                    "bank_info": bank.model_dump(),
                    "similarity_score": similarity,
                    "match_type": "exact" if similarity >= 0.95 else "fuzzy"
                })
        
        # Sort by similarity score (descending)
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Return top results
        return results[:max_results]
    
    async def execute(
        self,
        search_term: str,
        fuzzy_match: bool = True,
        max_results: int = 10
    ) -> ToolExecutionResult:
        """
        Execute bank lookup.
        
        Args:
            search_term: Bank name or identifier to search for
            fuzzy_match: Enable fuzzy matching (default: True)
            max_results: Maximum number of results (default: 10)
            
        Returns:
            ToolExecutionResult with matching banks
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(
                "Executing bank lookup",
                search_term=search_term,
                fuzzy_match=fuzzy_match,
                max_results=max_results
            )
            
            # Validate inputs
            if not search_term or len(search_term.strip()) < 2:
                raise ValueError("Search term must be at least 2 characters")
            
            if max_results < 1 or max_results > 50:
                raise ValueError("max_results must be between 1 and 50")
            
            # Simulate some processing time
            await asyncio.sleep(0.05 + len(search_term) * 0.001)
            
            # Search for banks
            matches = self._search_banks(search_term, fuzzy_match, max_results)
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            if not matches:
                self.logger.info(
                    "No banks found for search term",
                    search_term=search_term,
                    execution_time=execution_time
                )
                
                return ToolExecutionResult(
                    status=ToolStatus.SUCCESS,
                    data={
                        "banks": [],
                        "total_found": 0,
                        "search_term": search_term,
                        "message": f"No banks found matching '{search_term}'"
                    },
                    execution_time=execution_time,
                    tool_name=self.name
                )
            
            # Format results
            result_data = {
                "banks": matches,
                "total_found": len(matches),
                "search_term": search_term,
                "best_match": matches[0] if matches else None,
                "search_parameters": {
                    "fuzzy_match": fuzzy_match,
                    "max_results": max_results
                }
            }
            
            self.logger.info(
                "Bank lookup completed successfully",
                search_term=search_term,
                matches_found=len(matches),
                best_match_score=matches[0]["similarity_score"] if matches else 0,
                execution_time=execution_time
            )
            
            return ToolExecutionResult(
                status=ToolStatus.SUCCESS,
                data=result_data,
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except ValueError as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.logger.warning(
                "Bank lookup failed - validation error",
                search_term=search_term,
                error=str(e),
                execution_time=execution_time
            )
            
            return ToolExecutionResult(
                status=ToolStatus.ERROR,
                error=str(e),
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.logger.error(
                "Bank lookup failed - unexpected error",
                search_term=search_term,
                error=str(e),
                execution_time=execution_time
            )
            
            return ToolExecutionResult(
                status=ToolStatus.ERROR,
                error=f"Bank lookup failed: {str(e)}",
                execution_time=execution_time,
                tool_name=self.name
            )
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get OpenAI function schema for this tool.
        
        Returns:
            Function schema dictionary for OpenAI function calling
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_term": {
                            "type": "string",
                            "description": "Bank name or identifier to search for (e.g., 'Wells Fargo', 'Chase', 'Bank of America')"
                        },
                        "fuzzy_match": {
                            "type": "boolean",
                            "description": "Enable fuzzy matching for approximate name matching (default: true)",
                            "default": True
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (1-50, default: 10)",
                            "minimum": 1,
                            "maximum": 50,
                            "default": 10
                        }
                    },
                    "required": ["search_term"]
                }
            }
        }
    
    def get_bank_by_rssd_id(self, rssd_id: str) -> Optional[BankIdentification]:
        """
        Get bank information by RSSD ID.
        
        Args:
            rssd_id: Bank's RSSD identifier
            
        Returns:
            BankIdentification if found, None otherwise
        """
        for bank in self.bank_directory:
            if bank.rssd_id == rssd_id:
                return bank
        return None
    
    def get_all_banks(self) -> List[BankIdentification]:
        """
        Get list of all banks in the directory.
        
        Returns:
            List of all BankIdentification objects
        """
        return self.bank_directory.copy()
    
    def is_available(self) -> bool:
        """Check if the bank lookup service is available."""
        return self._enabled and bool(self.bank_directory)
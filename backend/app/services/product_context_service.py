from uuid import UUID

from sqlalchemy.orm import Session

from app.exceptions import AlreadyExistsError, NotFoundError
from app.models.product_context import ProductContext
from app.schemas.product_context import ProductContextCreateRequest, ProductContextUpdateRequest


def create_product_context(db: Session, org_id: UUID, data: ProductContextCreateRequest) -> ProductContext:
    """Create product context for org. Raises AlreadyExistsError if one already exists."""
    if has_product_context(db, org_id):
        raise AlreadyExistsError("Product context already exists for this organization.")
    ctx = ProductContext(
        org_id=org_id,
        product_name=data.product_name,
        product_description=data.product_description,
        existing_features=data.existing_features or [],
        target_users=data.target_users,
        known_limitations=data.known_limitations,
        additional_context=data.additional_context,
    )
    db.add(ctx)
    db.commit()
    db.refresh(ctx)
    return ctx


def get_product_context(db: Session, org_id: UUID) -> ProductContext:
    """Get product context for org. Raises NotFoundError if none."""
    ctx = db.query(ProductContext).filter(ProductContext.org_id == org_id).first()
    if ctx is None:
        raise NotFoundError("Product context not found.")
    return ctx


def update_product_context(db: Session, org_id: UUID, data: ProductContextUpdateRequest) -> ProductContext:
    """Update product context for org. Raises NotFoundError if none."""
    ctx = get_product_context(db, org_id)
    if data.product_name is not None:
        ctx.product_name = data.product_name
    if data.product_description is not None:
        ctx.product_description = data.product_description
    if data.existing_features is not None:
        ctx.existing_features = data.existing_features
    if data.target_users is not None:
        ctx.target_users = data.target_users
    if data.known_limitations is not None:
        ctx.known_limitations = data.known_limitations
    if data.additional_context is not None:
        ctx.additional_context = data.additional_context
    db.commit()
    db.refresh(ctx)
    return ctx


def has_product_context(db: Session, org_id: UUID) -> bool:
    """Return True if org has product context."""
    return db.query(ProductContext).filter(ProductContext.org_id == org_id).first() is not None

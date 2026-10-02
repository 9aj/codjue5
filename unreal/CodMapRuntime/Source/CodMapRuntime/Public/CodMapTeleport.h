#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Subsystems/WorldSubsystem.h"
#include "CodMapTeleport.generated.h"

class UStaticMeshComponent;
class APawn;

/** A world-wide per-pawn lock prevents immediate cycles across different portals. */
UCLASS()
class CODMAPRUNTIME_API UCodMapTeleportSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    bool Claim(APawn* Pawn, double Until);
    void Release(APawn* Pawn);
private:
    TMap<TWeakObjectPtr<APawn>, double> LockedUntil;
};

/** Teleport semantics are explicit configuration, never arbitrary GSC evaluation. */
UCLASS(Blueprintable)
class CODMAPRUNTIME_API ACodMapTeleport : public AActor
{
    GENERATED_BODY()
public:
    ACodMapTeleport();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="COD Map")
    TObjectPtr<UStaticMeshComponent> TriggerMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="COD Map")
    FVector Destination = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="COD Map")
    FRotator DestinationRotation = FRotator::ZeroRotator;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="COD Map")
    bool bSetView = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="COD Map")
    bool bSourceOriginAtFeet = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="COD Map", meta=(ClampMin="0"))
    float DelaySeconds = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="COD Map", meta=(ClampMin="0"))
    float CooldownSeconds = 0.5f;
protected:
    virtual void BeginPlay() override;
    UFUNCTION()
    void OnOverlap(UPrimitiveComponent* Overlapped, AActor* OtherActor,
        UPrimitiveComponent* OtherComponent, int32 BodyIndex, bool bSweep,
        const FHitResult& SweepResult);
    void Transport(TWeakObjectPtr<APawn> Pawn);
};

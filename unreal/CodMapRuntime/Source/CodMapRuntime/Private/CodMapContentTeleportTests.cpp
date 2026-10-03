#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/WorldSettings.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FCodMapContentTeleportTest, "CodMapRuntime.ContentOnlyTeleport",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FCodMapContentTeleportTest::RunTest(const FString&)
{
    FString ClassPath;
    if (!FParse::Value(FCommandLine::Get(), TEXT("CodJueTeleportTestClass="), ClassPath))
    {
        AddInfo(TEXT("Provide -CodJueTeleportTestClass with the generated synthetic fixture Blueprint class to run this integration test."));
        return true;
    }
    FVector ExpectedDestination(2600.96,0,365.12);
    FString ExpectedText;
    if (FParse::Value(FCommandLine::Get(), TEXT("CodJueExpectedDestination="), ExpectedText))
        if (!ExpectedDestination.InitFromString(ExpectedText)) { AddError(TEXT("Invalid expected destination"));return false; }
    const bool bInstant = FParse::Param(FCommandLine::Get(), TEXT("CodJueInstantTeleport"));
    UClass* PortalClass = LoadClass<AActor>(nullptr, *ClassPath);
    if (!TestNotNull(TEXT("Content-only Blueprint loads"), PortalClass)) return false;
    const auto Values = UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    GEngine->CreateNewWorldContext(EWorldType::Game).SetCurrentWorld(World);
    AActor* Portal = World->SpawnActor<AActor>(PortalClass);
    UBoxComponent* Box = Portal->FindComponentByClass<UBoxComponent>();
    if (!TestNotNull(TEXT("Engine box overlap component"), Box)) return false;
    Box->SetBoxExtent(FVector(200));
    Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Box->SetCollisionResponseToAllChannels(ECR_Ignore);
    Box->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
    Box->SetGenerateOverlapEvents(true);
    APawn* Pawn = World->SpawnActor<APawn>();
    UCapsuleComponent* Capsule = NewObject<UCapsuleComponent>(Pawn);
    Pawn->SetRootComponent(Capsule);Capsule->InitCapsuleSize(20,40);
    Capsule->SetCollisionProfileName(TEXT("Pawn"));Capsule->SetGenerateOverlapEvents(true);Capsule->RegisterComponent();
    Pawn->SetActorLocation(FVector(500,0,0));
    World->InitializeActorsForPlay(FURL());World->BeginPlay();
    World->GetWorldSettings()->NotifyBeginPlay();World->GetWorldSettings()->NotifyMatchStarted();
    auto Tick = [World]() { ++GFrameCounter;World->Tick(LEVELTICK_All,0.03f); };
    Pawn->SetActorLocation(FVector::ZeroVector);Capsule->UpdateOverlaps();
    TestTrue(TEXT("Blueprint claims shared pawn-root cooldown tag"), Capsule->ComponentTags.Contains(TEXT("CODJumpTeleportLock")));
    Tick();if (!bInstant) TestTrue(TEXT("Blueprint respects source delay"),Pawn->GetActorLocation().Equals(FVector::ZeroVector,1));
    for (int Index=0;Index<(bInstant ? 1 : 10);++Index) Tick();
    // Destination from map_pipeline/tests/test_conversion.fixture(), plus 40cm capsule half-height.
    TestTrue(TEXT("Blueprint applies destination and standing feet offset"),Pawn->GetActorLocation().Equals(ExpectedDestination,1));
    Pawn->SetActorLocation(FVector::ZeroVector);Capsule->UpdateOverlaps();
    for (int Index=0;Index<(bInstant ? 1 : 4);++Index) Tick();
    TestTrue(TEXT("Blueprint cooldown suppresses immediate reentry"),Pawn->GetActorLocation().Equals(FVector::ZeroVector,1));
    for (int Index=0;Index<15;++Index) Tick();
    TestFalse(TEXT("Shared cooldown tag is released"),Capsule->ComponentTags.Contains(TEXT("CODJumpTeleportLock")));
    World->EndPlay(EEndPlayReason::Quit);GEngine->DestroyWorldContext(World);World->DestroyWorld(false);
    return true;
}
#endif
